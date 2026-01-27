
import json
import time
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from vertex_utils import generate_message
from . import aggregator

logger = get_logger(__name__)

# =========================================================
# Sourcing Agent Prompts
# =========================================================

SOURCING_SYSTEM_INSTRUCTION = """
You are an industrial sourcing agent specialized in manufacturing equipment and production lines.
Your goal is to actively FIND real suppliers (OEMs, distributors, integrators, service partners) for industrial machines.
You follow a strict phased strategy and verify every source.
"""

PHASE_PLANNER_PROMPT = """
You are in PHASE {phase} of searching for suppliers for:
Machine: {machine_name}
Type: {machine_type}
Application: {application}
Target Country: Algeria

STRATEGY FOR THIS PHASE:
{phase_strategy}

CURRENT KNOWLEDGE:
{knowledge}

SEARCH HISTORY:
{history}

TASK:
1. Review the strategy for this phase.
2. Determine if you have enough info for this phase.
3. If not, generate EXACT search queries (max 3) to execute.
4. If yes, generate the findings for this phase.

OUTPUT FORMAT (JSON ONLY):
{{
  "status": "SEARCHING" or "PHASE_COMPLETE",
  "reasoning": "...",
  "queries": ["query 1", "query 2"],
  "findings": [
    {{
      "supplier_name": "...",
      "role": "OEM | Distributor | Integrator | Service",
      "region": "Algeria | MENA | France | Europe | USA | Global",
      "website": "...",
      "source_urls": ["..."],
      "confidence": "high | medium | low",
      "notes": "..."
    }}
  ]
}}
"""

EVALUATOR_PROMPT = """
You are an expert industrial researcher.
GOAL: Find real suppliers for {machine_name}.

NEW SEARCH RESULTS:
{results}

CURRENT KNOWLEDGE:
{knowledge}

TASK:
1. Extract REAL companies mentioned as manufacturers, distributors, or service providers.
2. Verify they are not marketplaces like Alibaba/Amazon.
3. Update knowledge with company names, roles, and websites.

OUTPUT FORMAT (JSON ONLY):
{{
  "new_suppliers": [...],
  "missing_info": "..."
}}
"""

# =========================================================
# Sourcing Agent Class
# =========================================================

class IndustrialSourcingAgent:
    def __init__(self):
        self.max_steps_per_phase = 2
        self.phases = [
            ("1", "OEM DISCOVERY (GLOBAL): Search for original manufacturers."),
            ("2", "OFFICIAL DISTRIBUTORS (ALGERIA): Search for local representation."),
            ("3", "REGIONAL FALLBACK: Expand to MENA, France, Europe, USA."),
            ("4", "SYSTEM INTEGRATORS: Turnkey production line suppliers."),
            ("5", "SERVICE & AFTER-SALES: Installation and maintenance.")
        ]

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        try:
            raw = generate_message(
                prompt=prompt,
                system_instruction=SOURCING_SYSTEM_INSTRUCTION,
                temperature=0.2
            )
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Sourcing Agent LLM call failed: {e}")
            return {}

    def find_suppliers(self, machine_name: str, machine_type: str = "", application: str = "") -> List[Dict[str, Any]]:
        knowledge = []
        history = []
        
        logger.info(f"START INDUSTRIAL SOURCING AGENT for: {machine_name}")

        for phase_num, phase_desc in self.phases:
            logger.info(f"Starting Phase {phase_num}: {phase_desc}")
            
            for step in range(self.max_steps_per_phase):
                # 1. Plan / Decide
                plan = self._call_llm(PHASE_PLANNER_PROMPT.format(
                    phase=phase_num,
                    machine_name=machine_name,
                    machine_type=machine_type,
                    application=application,
                    phase_strategy=phase_desc,
                    knowledge=json.dumps(knowledge, indent=2),
                    history="\n".join(history)
                ))

                if plan.get("status") == "PHASE_COMPLETE" or not plan.get("queries"):
                    if plan.get("findings"):
                        knowledge.extend(plan.get("findings"))
                    break

                # 2. Search
                queries = plan.get("queries", [])
                history.append(f"Phase {phase_num} Step {step}: {queries}")
                
                results_text = ""
                for q in queries:
                    try:
                        # Use existing search functionality
                        search_res = aggregator.search_machine_suppliers(q, max_total_results=3)
                        for r in search_res:
                            results_text += f"Source: {r.website}\nContent: Found {r.supplier_name} in {r.region}\n\n"
                    except Exception as e:
                        logger.warning(f"Search failed for {q}: {e}")

                # 3. Evaluate
                eval_res = self._call_llm(EVALUATOR_PROMPT.format(
                    machine_name=machine_name,
                    results=results_text,
                    knowledge=json.dumps(knowledge, indent=2)
                ))

                if eval_res.get("new_suppliers"):
                    knowledge.extend(eval_res.get("new_suppliers"))

        # Deduplicate and Clean
        unique_suppliers = {}
        for s in knowledge:
            name = s.get("supplier_name", "").strip().lower()
            if not name or "alibaba" in name or "indiamart" in name:
                continue
            if name not in unique_suppliers:
                unique_suppliers[name] = s
        
        return list(unique_suppliers.values())

sourcing_agent = IndustrialSourcingAgent()
