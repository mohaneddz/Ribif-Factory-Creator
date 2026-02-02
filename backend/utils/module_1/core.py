# backend/ribif_module_1.py
# RIBIF Module 1 — Vertex-only (Gemini) parallel 6-stage extraction (PDF/DOCX) -> JSON
# Goals:
# - All stages run IN PARALLEL (max_workers = number of sections)
# - NO nulls anywhere (always fill; guess if missing)
# - Remove "empty template" items (e.g. all-null machine row)
# - Faster + less "stuck": stage-specific relevant text slicing + timeout retry
# - Verbose prints: stage start/success/fail + provider + timing

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from dotenv import load_dotenv

from utils.logger import get_logger

logger = get_logger(__name__)

# =========================================================
# 0) Constants
# =========================================================

SYSTEM_INSTRUCTION = (
    "You are a business analyst and industrial engineer. "
    "Extract information from industrial project documents. "
    "Extract values that are EXPLICITLY stated in the document. "
    "For values not explicitly found, make reasonable engineering estimates based on the project type and industry. "
    "NEVER leave fields empty or null - always provide a value. "
    "For numbers, estimate based on typical industry values if not stated. "
    "Always return valid JSON only. "
    "DO NOT include any pricing/cost/budget/financial estimates."
)

STRICT_JSON_HEADER = (
    "OUTPUT RULES:\n"
    "1) Return ONLY a single valid JSON object.\n"
    "2) Use double quotes for all strings and keys.\n"
    "3) No markdown, no backticks, no commentary.\n"
    "4) CRITICAL: NEVER use 'N/A', null, or empty strings. Always provide realistic values:\n"
    "   - For strings: provide descriptive text based on context\n"
    "   - For numbers: estimate based on industry standards (e.g., quantity=1 if unknown)\n"
    "   - For lists: provide at least one relevant item\n"
    "5) Do NOT include trailing commas.\n"
    "6) Do NOT include empty/template items (no fully-empty objects in lists).\n\n"
)

DEFAULT_TIMEOUT_S = 60  # per stage; if exceeded, retry with smaller excerpt


# =========================================================
# 1) Document parsing (PDF/DOCX)
# =========================================================

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, List[str]]:
    doc = fitz.open(pdf_path)
    pages: List[str] = []
    for i in range(len(doc)):
        pages.append(doc[i].get_text("text") or "")
    doc.close()
    full = "\n".join([f"\n{'='*40}\nPAGE {i+1}\n{'='*40}\n{t}" for i, t in enumerate(pages)])
    return full.strip(), pages

def extract_text_from_docx(docx_path: str) -> Tuple[str, List[str]]:
    d = DocxDocument(docx_path)
    full = "\n".join(p.text for p in d.paragraphs).strip()
    # docx has no pages; treat as single "page"
    return full, [full]

def read_document_text(path: str) -> Tuple[str, List[str]]:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    if p.suffix.lower() == ".docx":
        return extract_text_from_docx(path)
    raise ValueError(f"Unsupported file type: {p.suffix}")


# =========================================================
# 2) JSON helpers
# =========================================================

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _short(s: str, n: int = 220) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "..."

def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _json_loads_relaxed(s: str) -> Dict[str, Any]:
    s = _strip_code_fences(s)

    # direct
    try:
        return json.loads(s)
    except Exception:
        # logger.warning("JSON direct parse failed, trying regex extraction") # optional: verbose
        pass

    # extract first {...}
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        raise ValueError("No JSON object found.")
    candidate = m.group(0)

    # common repairs
    candidate = candidate.replace("\u201c", '"').replace("\u201d", '"')
    candidate = candidate.replace("\u2019", "'")
    candidate = re.sub(r",\s*(?=[}\]])", "", candidate)  # trailing commas
    # last resort: single to double quotes
    candidate = candidate.replace("'", '"')

    return json.loads(candidate)

def _contains_null(obj: Any) -> bool:
    if obj is None:
        return True
    if isinstance(obj, dict):
        return any(_contains_null(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_null(v) for v in obj)
    return False

def _drop_empty_items(obj: Any) -> Any:
    """
    Remove list entries that are "empty templates":
    - dict where every leaf is None/""/[] or nested empty
    """
    def is_empty_leaf(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, str):
            s = v.strip().lower()
            if s == "" or s in ["n/a", "na", "n/a"]:
                return True
        if isinstance(v, list) and len(v) == 0:
            return True
        if isinstance(v, dict) and len(v) == 0:
            return True
        return False

    def is_empty_dict(d: Dict[str, Any]) -> bool:
        # recursively empty
        for vv in d.values():
            if isinstance(vv, dict):
                if not is_empty_dict(vv):
                    return False
            elif isinstance(vv, list):
                # if any non-empty element exists, not empty
                if any(not (isinstance(x, dict) and is_empty_dict(x)) and not is_empty_leaf(x) for x in vv):
                    return False
            else:
                if not is_empty_leaf(vv):
                    return False
        return True

    if isinstance(obj, dict):
        return {k: _drop_empty_items(v) for k, v in obj.items()}
    if isinstance(obj, list):
        new = []
        for item in obj:
            cleaned = _drop_empty_items(item)
            if isinstance(cleaned, dict) and is_empty_dict(cleaned):
                continue
            new.append(cleaned)
        return new
    return obj


# =========================================================
# 3) Relevant text slicing (speed + less stuck)
# =========================================================

def pick_relevant_pages(pages: List[str], keywords: List[str], max_pages: int = 4) -> List[int]:
    scores: List[Tuple[int, int]] = []
    kw = [k.lower() for k in keywords]
    for i, text in enumerate(pages):
        t = (text or "").lower()
        score = sum(t.count(k) for k in kw)
        scores.append((i, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    chosen = [i for i, s in scores if s > 0][:max_pages]
    if not chosen:
        # fallback: first pages
        chosen = list(range(min(max_pages, len(pages))))
    return sorted(set(chosen))

def build_excerpt(pages: List[str], page_ids: List[int], max_chars: int = 18000) -> str:
    parts = []
    for pid in page_ids:
        parts.append(f"\n{'='*40}\nPAGE {pid+1}\n{'='*40}\n{pages[pid]}\n")
    s = "".join(parts).strip()
    return s[:max_chars]


# =========================================================
# 4) Stage schema examples (used in prompt)
#    IMPORTANT: We keep the exact top-level JSON structure, but we never allow null.
# =========================================================

SCHEMA_STAGE_1 = {
    "informations_generales": {
        "nom_projet": "string",
        "nom_entreprise": "string",
        "raison_sociale": "string",
        "type_projet": "string",
        "secteur_activite": "string",
        "description_projet": "string",
        "objectifs_strategiques": ["string"],
        "localisation": {"pays": "string", "ville": "string", "zone": "string", "adresse": "string"},
        "taille_projet": {"echelle": "string", "superficie_estimee": "string"},
        "classification_danger": {"niveau_danger": "string", "type_dangers": ["string"]},
    }
}

SCHEMA_STAGE_2 = {
    "matieres_premieres": [
        {
            "nom_materiau": "string",
            "type": "string",
            "categorie": "string",
            "quantite_estimee": {"valeur": 0.0, "unite": "string", "periode": "string"},
            "specifications": "string",
            "qualite_requise": "string",
            "reglementations": ["string"],
        }
    ]
}

SCHEMA_STAGE_3 = {
    "produits_fabriques": [
        {
            "nom_produit": "string",
            "categorie": "string",
            "description": "string",
            "specifications_techniques": {
                "dimensions": "string",
                "poids": "string",
                "materiaux": "string",
                "normes": ["string"],
                "proprietes": "string",
            },
            "volume_production": {"capacite": "string_or_number", "unite": "string", "periode": "string"},
        }
    ]
}

SCHEMA_STAGE_4 = {
    "machines_production": [
        {
            "nom_machine": "string",
            "type": "string",
            "fabricant_recommande": "string",
            "quantite_necessaire": 1,
            "use": "string",
            "specifications": {"capacite": "string", "puissance": "string", "dimensions": "string", "alimentation": "string"},
            "performance": {"cadence": "string", "rendement": "string", "temps_cycle": "string"},
            "source_reference": "string",
        }
    ]
}

SCHEMA_STAGE_5 = {
    "processus_production": [
        {
            "numero_etape": 1,
            "nom_etape": "string",
            "description": "string",
            "machines_utilisees": ["string"],
        }
    ],
    "kpi_production": {
        "oee_cible": "string_percentage",
        "trs_cible": "string_percentage",
        "taux_rebut_acceptable": "string_percentage",
        "temps_changement_serie": "string_duration",
    },
}

SCHEMA_STAGE_6 = {
    "aspects_reglementaires": {
        "autorisations_requises": ["string"],
        "normes_applicables": ["string"],
        "certifications": ["string"],
        "contraintes_environnementales": ["string"],
        "produits_dangereux": [{"produit": "string", "classification": "string", "autorite": "string"}],
    },
    "analyse_risques": {
        "risques_techniques": ["string"],
        "risques_reglementaires": ["string"],
        "risques_marche": ["string"],
        "strategies_mitigation": ["string"],
    },
    "opportunites": {"innovation": "string", "marche": "string", "partenariats": "string", "subventions": "string"},
    "recommandations": ["string"],
}


# =========================================================
# 5) Prompt builder
# =========================================================

def build_stage_prompt(stage_key: str, schema_example: Dict[str, Any], excerpt: str) -> str:
    base = (
        "LANGUAGE RULE:\n"
        "- If the document is in French -> respond in French\n"
        "- If the document is in English -> respond in English\n"
        "- Match the document language exactly\n\n"
        "ABSOLUTE RULES:\n"
        "- Extract information from the document first\n"
        "- If information is NOT in the document, provide realistic engineering estimates based on project type\n"
        "- NEVER use 'N/A', null, or empty values - always fill with reasonable estimates\n"
        "- For quantities, default to 1 if not specified\n"
        "- For specifications, use typical industry values\n"
        "- Do NOT output empty/template objects in lists.\n"
        "- Do NOT include any pricing/cost/budget.\n\n"
        "REQUIRED JSON STRUCTURE (must match exactly):\n"
        f"{json.dumps(schema_example, ensure_ascii=False, indent=2)}\n\n"
        "DOCUMENT EXCERPT:\n"
        f"{excerpt}\n\n"
        "Return ONLY the JSON object with ALL fields populated (no nulls/N/A)."
    )

    if stage_key == "stage_4_machines_equipements":
        return (
            "You are an industrial engineer.\n"
            "Task: Extract the production machines mentioned in the document.\n"
            "REQUIREMENTS:\n"
            "1. Include all machines mentioned for production processes\n"
            "2. For each machine, fill ALL specification fields:\n"
            "   - capacite: Estimate based on machine type if not stated\n"
            "   - puissance: Estimate typical power for this machine type\n"
            "   - dimensions: Provide typical dimensions for the machine category\n"
            "   - alimentation: Default to '380V triphasé' if not specified\n"
            "3. For quantite_necessaire: Use exact number if stated, otherwise estimate based on production needs (minimum 1)\n"
            "4. For fabricant_recommande: Use brand if stated, otherwise suggest typical manufacturers for this machine type\n"
            "5. NEVER use 'N/A' or null - always provide realistic values\n\n"
            + base
        )

    return (
        "Task: extract information from the document.\n"
        "Extract explicit data first. For missing fields, provide reasonable estimates based on the project context.\n"
        "NEVER use 'N/A', null, or empty strings - always fill with realistic values.\n\n"
        + base
    )


# =========================================================
# 6) Vertex-only LLM client wrapper
# =========================================================

class VertexJSON:
    def __init__(self):
        load_dotenv()
        self.vertex_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    def generate_raw(self, prompt: str, temperature: float) -> str:
        # Uses your provided signature
        from vertex_utils import generate_message
        return generate_message(
            prompt=STRICT_JSON_HEADER + prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            top_p=0.95,
        )

    def generate_json(self, prompt: str, temperature: float, tag: str) -> Dict[str, Any]:
        raw = self.generate_raw(prompt, temperature)
        try:
            return _json_loads_relaxed(raw)
        except Exception as e:
            logger.warning("%s: JSON parse failed -> %s", tag, e)
            logger.warning("Raw head: %s", _short(raw))
            
            # Save raw output for debugging
            try:
                debug_dir = Path("data/debug_dumps")
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = debug_dir / f"{tag}_failed_{timestamp}.txt"
                debug_file.write_text(raw, encoding="utf-8")
                logger.info("Saved raw failed output to %s", debug_file)
            except Exception as dump_err:
                logger.error("Failed to save debug dump: %s", dump_err)

            # One repair attempt
            repair = (
                "Your previous output was NOT valid JSON.\n"
                "Return ONLY one valid JSON object, no text.\n"
                "For missing information, provide realistic estimates - NEVER use 'N/A' or null.\n"
                "All fields must have values.\n\n"
                f"ORIGINAL REQUEST:\n{prompt}\n\n"
                "BROKEN OUTPUT:\n"
                f"{raw}\n"
            )
            raw2 = self.generate_raw(repair, temperature=0.0)
            data2 = _json_loads_relaxed(raw2)
            return data2


# =========================================================
# 7) Main extractor (parallel stages + global null filler)
# =========================================================

class RIBIFExtractor:
    def __init__(self):
        self.llm = VertexJSON()
        logger.info("RIBIF Module1 ready (parallel, Vertex-only)")
        logger.info("Vertex requested model: %s", self.llm.vertex_model)

    def _run_stage(self, stage_key: str, schema: Dict[str, Any], excerpt: str, temperature: float) -> Dict[str, Any]:
        prompt = build_stage_prompt(stage_key, schema, excerpt)
        return self.llm.generate_json(prompt, temperature=temperature, tag=stage_key)

    # _global_fill_no_nulls removed to prevent fabrication.

    def process_document(
        self,
        document_path: str,
        output_dir: str = "data/extracted_data",
        max_workers: int = 7,  # 6 stages + metadata/extras margin
        max_pages_per_stage: int = 4,
        excerpt_chars: int = 18000,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> Dict[str, Any]:
        p = Path(document_path)
        if not p.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")

        logger.info("=" * 70)
        logger.info("START RIBIF MODULE 1 — Parallel Extraction (Vertex-only)")
        logger.info("Input: %s", p.name)
        logger.info("max_workers: %s", max_workers)
        logger.info("pages/stage: %s | excerpt_chars: %s", max_pages_per_stage, excerpt_chars)
        logger.info("=" * 70)

        t0 = time.time()
        full_text, pages = read_document_text(str(p))

        # keyword packs for relevance
        stage_keywords = {
            "stage_1_informations_generales": ["projet", "entreprise", "raison sociale", "localisation", "site", "objectif", "description"],
            "stage_2_matieres_premieres": ["matière", "matières", "raw", "résine", "poly", "additif", "solvant", "isocyanate", "polyol", "verre"],
            "stage_3_produits_fabriques": ["produit", "gamme", "fabrication", "menuiserie", "revêtement", "composite", "verre", "solution"],
            "stage_4_machines_equipements": ["machine", "équipement", "injection", "extrusion", "moulage", "ligne", "automate", "robot", "presse"],
            "stage_5_processus_production": ["processus", "étape", "flux", "production", "ligne", "contrôle", "assemblage", "cycle", "kpi", "oee", "trs"],
            "stage_6_informations_complementaires": ["réglement", "norme", "certification", "autorisation", "risque", "environnement", "danger", "andi"],
        }

        # build excerpts per stage
        excerpts: Dict[str, str] = {}
        for sk, kws in stage_keywords.items():
            page_ids = pick_relevant_pages(pages, kws, max_pages=max_pages_per_stage)
            excerpts[sk] = build_excerpt(pages, page_ids, max_chars=excerpt_chars)

        # stage configs
        stage_jobs = [
            ("stage_1_informations_generales", SCHEMA_STAGE_1, 0.1),
            ("stage_2_matieres_premieres", SCHEMA_STAGE_2, 0.2),
            ("stage_3_produits_fabriques", SCHEMA_STAGE_3, 0.2),
            ("stage_4_machines_equipements", SCHEMA_STAGE_4, 0.2),  # NOT strict anymore; we want NO nulls
            ("stage_5_processus_production", SCHEMA_STAGE_5, 0.2),
            ("stage_6_informations_complementaires", SCHEMA_STAGE_6, 0.3),
        ]

        results: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []

        def submit_stage(ex, stage_key: str, schema: Dict[str, Any], temp: float):
            excerpt = excerpts[stage_key]
            return ex.submit(self._run_stage, stage_key, schema, excerpt, temp)

        logger.info("START Launching stages in parallel...")
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_map = {}
            for stage_key, schema, temp in stage_jobs:
                logger.info("START %s SUBMIT", stage_key)
                fut = submit_stage(ex, stage_key, schema, temp)
                future_map[fut] = (stage_key, schema, temp, excerpts[stage_key])

            # Option B: iterate futures and call result(timeout=timeout_s)
            futures_list = list(future_map.keys())
            for fut in futures_list:
                stage_key, schema, temp, start_excerpt = future_map[fut]
                try:
                    # Enforce strict per-stage timeout check
                    data = fut.result(timeout=timeout_s)
                    # drop empty template items
                    data = _drop_empty_items(data)
                    results[stage_key] = data
                    
                    extra = ""
                    if stage_key == "stage_2_matieres_premieres":
                        extra = f" | count={len(data.get('matieres_premieres', []))}"
                    if stage_key == "stage_3_produits_fabriques":
                        extra = f" | count={len(data.get('produits_fabriques', []))}"
                    if stage_key == "stage_4_machines_equipements":
                        extra = f" | count={len(data.get('machines_production', []))}"
                    if stage_key == "stage_5_processus_production":
                        extra = f" | steps={len(data.get('processus_production', []))}"
                    logger.info("DONE %s%s", stage_key, extra)
                    
                except FuturesTimeoutError:
                    warnings.append(f"{stage_key}: timeout after {timeout_s}s, retrying with smaller excerpt")
                    logger.warning("TIMEOUT %s -> retry smaller excerpt", stage_key)
                    
                    # Cancel the stuck future
                    fut.cancel()
                    
                    try:
                        smaller = start_excerpt[:6000]
                        prompt = build_stage_prompt(stage_key, schema, smaller)
                        # synchronous retry
                        data = self.llm.generate_json(prompt, temperature=0.0, tag=stage_key + "_retry_small")
                        data = _drop_empty_items(data)
                        results[stage_key] = data
                        logger.info("DONE %s RETRY SUCCESS", stage_key)
                    except Exception as e2:
                        warnings.append(f"{stage_key}: retry failed: {e2}")
                        logger.error("ERROR %s RETRY FAIL -> %s", stage_key, e2)
                        results[stage_key] = {}
                        
                except Exception as e:
                    warnings.append(f"{stage_key}: failed: {e}")
                    logger.error("ERROR %s FAIL -> %s", stage_key, e)
                    results[stage_key] = {}

        # Build final JSON (exact format)
        processing_time = round(time.time() - t0, 3)

        meta_note = "Document extraction with intelligent estimation. All fields populated (no nulls)."
        if warnings:
            meta_note = (meta_note + " | WARNINGS: " + " ; ".join(warnings))[:4000]

        final_json: Dict[str, Any] = {
            "ribif_metadata": {
                "extraction_method": "Module1 Parallel 6-stage (Vertex Gemini + No-Nulls)",
                "extraction_date": _now_iso(),
                "model_used": self.llm.vertex_model,
                "api_provider": "Vertex",
                "extraction_mode": "Document + Industry Guessing (no nulls)",
                "ribif_modules_support": [1],
                "note": meta_note,
                "processing_time_seconds": processing_time,
                "source_file": p.name,
            },
            "stage_1_informations_generales": results.get("stage_1_informations_generales", {}),
            "stage_2_matieres_premieres": results.get("stage_2_matieres_premieres", {}),
            "stage_3_produits_fabriques": results.get("stage_3_produits_fabriques", {}),
            "stage_4_machines_equipements": results.get("stage_4_machines_equipements", {}),
            "stage_5_processus_production": results.get("stage_5_processus_production", {}),
            "stage_6_informations_complementaires": results.get("stage_6_informations_complementaires", {}),
        }

        # Final cleanup: remove empty template list rows
        final_json = _drop_empty_items(final_json)
        # NOTE: We no longer call _global_fill_no_nulls because we want to preserve
        # "N/A" and missing values rather than fabricating data.

        # Web enrichment is now handled by the RIBIFEnricher in the pipeline route.

        # Save
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"module_1.json"
        out_file.write_text(json.dumps(final_json, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info("=" * 70)
        logger.info("DONE MODULE 1")
        logger.info("Time: %.2fs", processing_time)
        logger.info("Saved: %s", out_file.resolve())
        if warnings:
            logger.warning("Warnings: %s (see ribif_metadata.note)", len(warnings))
        logger.info("=" * 70)

        return final_json


# =========================================================
# 8) CLI
# =========================================================
