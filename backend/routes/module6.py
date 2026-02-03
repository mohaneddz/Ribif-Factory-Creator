import json
from datetime import date
from flask import Blueprint, jsonify, request

from config import OUTPUT_DIRS, SKIP_MODULE_6, write_json
from supabase_utils import get_supabase, insert_tco_run
# Heavy imports moved to lazy loading for faster startup
from utils.logger import log_skip, get_logger
from utils.module_6.core import (
    compute_input_fingerprint,
    MODULE6_VERSION,
    RIBIFModule6TCO,
    ProductTCO,
    RawMaterialTCO,
    get_heuristic_machine_estimate,
)
from utils.app_helpers import (
    get_request_project_id,
    get_request_user_id,
    insert_tco_details,
    load_template_payload,
    upload_and_register_file,
    sanitize_for_json,
)
from werkzeug.exceptions import ClientDisconnected

logger = get_logger("module6")

bp_module6 = Blueprint("module6", __name__)

# In-memory cache for idempotency (project_id, version, fingerprint) -> result
_module6_cache = {}
_module6_running = set()  # Set of (project_id, version, fingerprint) currently running


def _get_idempotency_key(project_id: str, fingerprint: str) -> tuple:
    """Generate idempotency key tuple."""
    return (project_id or "unknown", MODULE6_VERSION, fingerprint)


def _get_deterministic_output_path(fingerprint: str) -> str:
    """Generate deterministic output file path based on fingerprint."""
    return OUTPUT_DIRS["module6"] / f"{MODULE6_VERSION}_{fingerprint}.json"


@bp_module6.route("/api/module6/tco-from-sourcing", methods=["POST"])
def calculate_tco_from_sourcing():
    global _module6_cache, _module6_running
    
    try:
        if SKIP_MODULE_6:
            log_skip("module6.calculate_tco_from_sourcing", reason="SKIP_MODULE_6")
            payload = load_template_payload("module6") or {}
            project_id = get_request_project_id(include_json=True)
            if isinstance(payload, dict) and project_id:
                payload["project_id"] = payload.get("project_id") or project_id
            return jsonify(payload)

        # Get project_id from headers first to avoid reading large payload just for this
        project_id = request.headers.get("x-project-id") or request.headers.get("X-Project-Id")
        module4_id = None

        if not request.is_json:
            return jsonify({"error": "Expected JSON input"}), 400

        try:
            data = request.get_json()
        except ClientDisconnected:
            logger.error("Client disconnected while reading request body - payload may be too large")
            return jsonify({"error": "Request interrupted - try reducing payload size"}), 400
        
        if "data" in data:
            data = data["data"]

        # Get project_id from data if not in headers
        if not project_id:
            project_id = data.get("project_id") or data.get("ribif_metadata", {}).get("project_id")

        module4_id = data.get("module4_id") or data.get("ribif_metadata", {}).get("module4_id")

        # Compute input fingerprint for idempotency
        fingerprint = compute_input_fingerprint(data)
        idempotency_key = _get_idempotency_key(project_id, fingerprint)
        
        # Check if we already have a successful result
        if idempotency_key in _module6_cache:
            cached = _module6_cache[idempotency_key]
            logger.info("Returning cached Module 6 result for fingerprint %s (idempotent)", fingerprint)
            return jsonify(cached)
        
        # Check if currently running
        if idempotency_key in _module6_running:
            logger.info("Module 6 already running for fingerprint %s, returning status", fingerprint)
            return jsonify({"status": "running", "fingerprint": fingerprint})
        
        # Check if deterministic output file already exists
        output_file = _get_deterministic_output_path(fingerprint)
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    cached_result = json.load(f)
                if project_id:
                    cached_result["project_id"] = project_id
                _module6_cache[idempotency_key] = cached_result
                logger.info("Returning existing file result for fingerprint %s", fingerprint)
                return jsonify(cached_result)
            except Exception as e:
                logger.warning("Could not load cached file %s: %s", output_file, e)
        
        # Mark as running
        _module6_running.add(idempotency_key)
        
        try:
            machines_enriched = data.get("machines_enriched", [])
            ribif_metadata = data.get("ribif_metadata", {})

            stage_1 = data.get("stage_1_informations_generales", {})
            stage_2 = data.get("stage_2_matieres_premieres", {})
            stage_3 = data.get("stage_3_produits_fabriques", {})
            stage_4 = data.get("stage_4_machines_equipements", {})
            stage_5 = data.get("stage_5_processus_production", {})
            stage_6 = data.get("stage_6_informations_complementaires", {})

            if not machines_enriched:
                _module6_running.discard(idempotency_key)
                return jsonify({"error": "No enriched machines found in input"}), 400

            tco_calculator = RIBIFModule6TCO()
            
            # Prepare all machines for BATCH estimation (single LLM call)
            machine_inputs = []
            suppliers_map = {}
            
            for idx, machine_item in enumerate(machines_enriched, 1):
                machine_input_raw = machine_item.get("machine_input", {})
                suppliers_raw = machine_item.get("suppliers", [])
                
                machine_name = machine_input_raw.get("nom_machine", f"Machine_{idx}")
                
                tco_machine_input = {
                    "id": f"machine_{idx}",
                    "name": machine_name,
                    "category": machine_input_raw.get("type", "Industrial Equipment"),
                    "manufacturer": machine_input_raw.get("fabricant_recommande", "Unknown"),
                    "base_model": machine_input_raw.get("type", ""),
                    "original_specs": {
                        "capacite": machine_input_raw.get("specifications", {}).get("capacite", ""),
                        "puissance": machine_input_raw.get("specifications", {}).get("puissance", ""),
                        "dimensions": machine_input_raw.get("specifications", {}).get("dimensions", {}),
                        "poids": machine_input_raw.get("specifications", {}).get("poids", ""),
                        "alimentation": machine_input_raw.get("specifications", {}).get("alimentation", ""),
                    },
                }
                machine_inputs.append(tco_machine_input)
                
                # Build suppliers map for batch estimation
                if suppliers_raw:
                    sorted_suppliers = sorted(
                        suppliers_raw,
                        key=lambda x: x.get("relevance_score", 0),
                        reverse=True,
                    )
                    suppliers_map[machine_name] = [{
                        "supplier_name": s.get("supplier_name", "Unknown"),
                        "website": s.get("website", ""),
                        "region": s.get("region", "Global"),
                        "price_estimate": s.get("price_estimate"),
                        "source": s.get("source", "Module 4 Enrichment"),
                        "notes": s.get("notes", ""),
                        "relevance_score": s.get("relevance_score", 0),
                    } for s in sorted_suppliers[:3]]
            
            # BATCH estimate all machines in ONE LLM call
            logger.info("Starting BATCH TCO estimation for %d machines", len(machine_inputs))
            batch_estimates = tco_calculator.estimate_machines_batch(machine_inputs, suppliers_map)
            
            all_machine_tcos = []
            all_product_tcos = []
            
            for machine_input in machine_inputs:
                machine_name = machine_input["name"]
                
                # Get batch estimate or fall back to heuristic
                estimate = batch_estimates.get(machine_name)
                if not estimate:
                    logger.warning("No batch estimate for '%s', using heuristic", machine_name)
                    estimate = get_heuristic_machine_estimate(machine_name, machine_input.get("category", ""))
                
                # Calculate TCO from estimate
                machine_tco = tco_calculator.calculate_machine_tco(
                    machine_input=machine_input,
                    suppliers=suppliers_map.get(machine_name, []),
                    use_llm=False,  # Don't call LLM again - use pre-computed estimate
                    precomputed_estimate=estimate,
                )
                all_machine_tcos.append(machine_tco)

            products = stage_3.get("produits_fabriques", [])
            if isinstance(products, dict):
                products = products.get("produits_fabriques", [])
            if products:
                avg_machine_annual = 0
                if all_machine_tcos:
                    avg_machine_annual = sum(m.annual_tco for m in all_machine_tcos) / max(len(all_machine_tcos), 1)

                # Use LLM to estimate product costs based on context
                product_estimates = tco_calculator.estimate_product_costs(
                    products=products,
                    avg_machine_annual=avg_machine_annual,
                    stage_1=stage_1,
                    stage_3=stage_3,
                )

                for product in products:
                    nom_produit = product.get("nom_produit", "Unknown")
                    categorie = product.get("categorie", "finished")
                    
                    # Get LLM estimates for this product
                    estimate = product_estimates.get(nom_produit, {})
                    landing_cost = float(estimate.get("landing_cost", avg_machine_annual * 0.03))
                    holding_cost = float(estimate.get("holding_cost", avg_machine_annual * 0.02))
                    quality_cost = float(estimate.get("quality_cost", avg_machine_annual * 0.015))
                    administrative_cost = float(estimate.get("administrative_cost", avg_machine_annual * 0.01))

                    all_product_tcos.append(ProductTCO(
                        nom_produit=nom_produit,
                        categorie=categorie,
                        landing_cost=round(landing_cost, 2),
                        holding_cost=round(holding_cost, 2),
                        quality_cost=round(quality_cost, 2),
                        administrative_cost=round(administrative_cost, 2),
                        total_tco=round(landing_cost + holding_cost + quality_cost + administrative_cost, 2),
                    ))

            raw_material_tcos = []
            matieres = stage_2.get("matieres_premieres", [])
            if isinstance(matieres, dict):
                raw_materials = matieres.get("matieres_premieres", [])
            elif isinstance(matieres, list):
                raw_materials = matieres
            else:
                raw_materials = []

            if raw_materials:
                raw_material_results = tco_calculator.estimate_raw_material_costs(raw_materials, use_llm=True)
                for rm in raw_material_results:
                    raw_material_tcos.append(RawMaterialTCO(**rm))

            annual_tco = tco_calculator.calculate_annual_tco(
                machine_tcos=all_machine_tcos,
                product_tcos=all_product_tcos,
                raw_material_tcos=raw_material_tcos,
                years=5,
            )

            total_machines_tco = sum(m.total_tco for m in all_machine_tcos)
            total_products_tco = sum(p.total_tco for p in all_product_tcos)
            total_raw_materials_tco = sum(r.total_tco for r in raw_material_tcos)
            total_tco = total_machines_tco + total_products_tco + total_raw_materials_tco

            info_generales = stage_1.get("informations_generales", {})
            company_name = info_generales.get("nom_entreprise", ribif_metadata.get("company_name", "Unknown Company"))
            project_name = info_generales.get("nom_projet", ribif_metadata.get("project_name", "Unknown Project"))

            result = {
                "company_name": company_name,
                "project_name": project_name,
                "calculation_date": str(date.today()),
                "total_tco": round(total_tco, 2),
                "average_annual_tco": round(total_tco / 5, 2),
                "tco_per_unit_revenue": 0,
                "machine_tco": [m.model_dump() for m in all_machine_tcos],
                "total_machines_tco": round(total_machines_tco, 2),
                "product_tco": [p.model_dump() for p in all_product_tcos],
                "total_products_tco": round(total_products_tco, 2),
                "raw_materials_tco": [r.model_dump() for r in raw_material_tcos],
                "total_raw_materials_tco": round(total_raw_materials_tco, 2),
                "annual_tco": [a.model_dump() for a in annual_tco],
                "stage_1_informations_generales": stage_1,
                "stage_2_matieres_premieres": stage_2,
                "stage_3_produits_fabriques": stage_3,
                "stage_4_machines_equipements": stage_4,
                "stage_5_processus_production": stage_5,
                "stage_6_informations_complementaires": stage_6,
                "sourcing_metadata": ribif_metadata,
            }

            if project_id:
                result["project_id"] = project_id

            # Add fingerprint and version to result
            result["module6_version"] = MODULE6_VERSION
            result["input_fingerprint"] = fingerprint

            # Use deterministic output path
            write_json(output_file, result)

            tco_run_id = None
            client = get_supabase()
            owner_id = get_request_user_id()
            if client and project_id:
                try:
                    tco_run_id = insert_tco_run(client, project_id, module4_id, result)
                    if tco_run_id:
                        insert_tco_details(client, tco_run_id, result)
                    if output_file.exists():
                        # Check if file already uploaded with same fingerprint
                        output_file_id, output_file_url = upload_and_register_file(
                            client=client,
                            project_id=project_id,
                            owner_id=owner_id,
                            local_path=str(output_file),
                            category="module6-output",
                            label=output_file.name,
                        )
                        result.setdefault("sourcing_metadata", {})
                        result["sourcing_metadata"]["module6_output_file_id"] = output_file_id
                        result["sourcing_metadata"]["module6_output_file_url"] = output_file_url
                except Exception:
                    pass

            if tco_run_id:
                result["tco_run_id"] = tco_run_id

            # Cache the result and clear running status
            _module6_cache[idempotency_key] = sanitize_for_json(result)
            _module6_running.discard(idempotency_key)

            return jsonify(sanitize_for_json(result))
        
        finally:
            # Ensure running status is cleared even on error within try block
            _module6_running.discard(idempotency_key)
        
    except Exception as e:
        # Clear running status on error
        try:
            if idempotency_key:
                _module6_running.discard(idempotency_key)
        except NameError:
            pass
        logger.exception("Module 6 failed with critical error")
        return jsonify({"error": str(e), "status": "error"}), 500


@bp_module6.route("/api/module6/tco", methods=["POST"])
def calculate_tco():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        if "machine_input" not in data:
            return jsonify({"error": "Missing required field: machine_input"}), 400
        tco_calculator = RIBIFModule6TCO()
        result = tco_calculator.process_input(data)
        if "error" in result:
            return jsonify(result), 400
        return jsonify({"message": "TCO calculated successfully", "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
