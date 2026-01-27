"""
Agentic Web Search Module
-------------------------
HARDENED: Implements quota-aware AI-driven search loop with rate limiting.
"""

from __future__ import annotations

import json
import time
import os
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from . import aggregator
from .base import SupplierResult, MachineSpecsResult, ImageResult
from vertex_utils import generate_message
from utils.logger import get_logger
from utils.quota_manager import with_rate_limit, with_retry, is_quota_error, get_user_friendly_error
from utils.normalization import normalize_numeric

logger = get_logger(__name__)

# =========================================================
# Configuration
# =========================================================

MAX_STEPS = 1  # Reduced to 1 for speed (was 3)
LLM_TIMEOUT = 60
TEMPERATURE = 0.2

# =========================================================
# Prompts
# =========================================================

PLANNER_PROMPT = """
You are an expert industrial researcher. Your goal is: "{goal}".
Step {step} of {max_steps} in the search process.

CURRENT KNOWLEDGE:
{knowledge}

MISSING / UNCERTAIN INFO:
{missing}

SEARCH HISTORY:
{history}

TIPS:
- Use ONE broad query that can find manufacturer names
- Prefer general searches over specific model lookups
- If you have ANY manufacturer name or machine category, choose FINISH

DECISION:
Determine the next best step.
- If you have a manufacturer name OR machine type, choose "FINISH" (we can estimate everything else)
- If you have ANY useful information, choose "FINISH" (estimation is faster)
- Only choose "SEARCH" if you have absolutely ZERO information
- If searching, provide only 1 query

OUTPUT FORMAT (JSON ONLY):
{{
  "action": "SEARCH" or "FINISH",
  "reasoning": "Why you made this decision",
  "search_queries": ["query 1"] (if action is SEARCH, only 1 query),
  "final_answer": {{ ... }} (if action is FINISH, provide the structured answer matching the goal)
}}
"""

EVALUATOR_PROMPT = """
You are an expert industrial researcher.
GOAL: "{goal}"

NEW SEARCH RESULTS:
{results}

CURRENT KNOWLEDGE:
{knowledge}

TASK:
1. Extract relevant facts from the NEW SEARCH RESULTS that help achieve the GOAL.
2. Update the CURRENT KNOWLEDGE with these facts.
3. Identify what is still MISSING or needs verification.
4. Ignore irrelevant or low-quality results.

OUTPUT FORMAT (JSON ONLY):
{{
  "new_facts": {{ "field": "value", ... }},
  "updated_knowledge": {{ ... }},
  "missing_info": ["what is still missing"],
  "quality_assessment": "Low/Medium/High confidence in these results"
}}
"""

# =========================================================
# Classes
# =========================================================

@dataclass
class AgentState:
    goal: str
    knowledge: Dict[str, Any] = field(default_factory=dict)
    missing: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    steps_taken: int = 0

class AgenticSearch:
    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    def _call_llm(self, prompt: str, tag: str) -> Dict[str, Any]:
        """
        HARDENED: Helper to call LLM with retry logic and quota awareness.
        """
        raw = ""
        try:
            @with_retry(max_attempts=2, catch_quota_errors=True)
            def _make_call():
                result = generate_message(
                    prompt=prompt,
                    temperature=TEMPERATURE,
                    system_instruction="You are a helpful industrial research assistant. meaningful/valid JSON only.",
                )
                if not result:
                    raise ValueError("Empty response from LLM")
                return result
            
            raw = _make_call()
            
            # 1. Robust cleanup
            cleaned = (raw or "").strip()
            
            # Remove Markdown code fences if present
            if "```" in cleaned:
                # Find the content between first and last triple backticks
                m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
                if m:
                    cleaned = m.group(1).strip()
            
            # 2. Try direct parse
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
                
            # 3. Extract first valid JSON object or array
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Agentic LLM call '{tag}' failed to parse JSON. Raw (truncated): {cleaned[:1000]}")
            return {}
            
        except Exception as e:
            if is_quota_error(e):
                error_info = get_user_friendly_error(e)
                logger.error(f"Agentic '{tag}' quota error: {error_info['message']}")
            else:
                logger.error(f"Agentic LLM call '{tag}' failed: {e}")
            
            if raw:
                logger.error(f"Raw output (truncated): {raw[:1000]}")
            
            return {}

    @with_rate_limit("web_search", min_delay=0.5)
    def _execute_search(self, queries: List[str], search_type: str) -> str:
        """
        HARDENED: Executes search using aggregator with rate limiting.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def _search_one(q: str) -> str:
            try:
                if search_type == "specs":
                    res = aggregator.search_machine_specs(q, max_search_results=5)
                    return f"Query: {q}\nDatasheets: {res.datasheet_urls}\nSources: {res.sources}\n"
                elif search_type == "suppliers":
                    res = aggregator.search_machine_suppliers(q, max_total_results=5)
                    summary = f"Query: {q}\nFound {len(res)} suppliers.\n"
                    for s in res:
                        summary += f"- {s.supplier_name} ({s.region}, {s.price_estimate})\n"
                    return summary
            except Exception as e:
                return f"Query: {q} failed: {e}"
            return ""
        
        results_summary = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(_search_one, q) for q in queries]
            for fut in as_completed(futures):
                try:
                    results_summary.append(fut.result())
                except Exception:
                    pass
        
        return "\n".join(results_summary)

    def search_specs_agentic(self, machine_name: str, manufacturer: str = "") -> MachineSpecsResult:
        """
        Agentic loop to find machine specs.
        """
        initial_goal = f"Find detailed specifications for machine '{machine_name}' by '{manufacturer}'. Need: dimensions, power, weight, capacity."
        state = AgentState(goal=initial_goal, missing=["dimensions", "power", "weight", "capacity"])
        
        # Initial knowledge
        state.knowledge = {"machine": machine_name, "manufacturer": manufacturer}

        logger.info(f"START AGENTIC SEARCH SPECS: {machine_name}")

        final_specs = MachineSpecsResult(model=machine_name, manufacturer=manufacturer)

        for step in range(MAX_STEPS):
            # 1. PLAN
            prompt = PLANNER_PROMPT.format(
                goal=state.goal,
                step=step + 1,
                max_steps=MAX_STEPS,
                knowledge=json.dumps(state.knowledge, indent=2),
                missing=json.dumps(state.missing),
                history="\n".join(state.history)
            )
            plan = self._call_llm(prompt, f"plan_step_{step}")
            
            action = plan.get("action", "FINISH")
            
            if action == "FINISH" or step == MAX_STEPS - 1:
                # We are done, parse final answer
                final_data = plan.get("final_answer", {})
                # Merge into MachineSpecsResult
                if final_data:
                    final_specs.specifications = final_data.get("specifications", final_specs.specifications)
                    # Try to extract URLs if LLM put them in final answer
                    # (This part relies on LLM understanding the schema or extracting from text)
                break
            
            # 2. ACT (SEARCH)
            queries = plan.get("search_queries", [])
            if not queries:
                # If SEARCH but no queries, default to machine name
                queries = [f"{manufacturer} {machine_name} specifications"]
            
            state.history.append(f"Step {step}: Searching {queries}")
            
            # Execute search
            search_output = self._execute_search(queries, "specs")
            
            # 3. OBSERVE & EVALUATE
            eval_prompt = EVALUATOR_PROMPT.format(
                goal=state.goal,
                results=search_output,
                knowledge=json.dumps(state.knowledge, indent=2)
            )
            evaluation = self._call_llm(eval_prompt, f"eval_step_{step}")
            
            # Update state
            new_facts = evaluation.get("new_facts", {})
            state.knowledge.update(new_facts)
            state.missing = evaluation.get("missing_info", [])
            
            # Also gather raw URLs/sources from the actual search execution
            # (In a real implementation we'd pass the structured results object, here we parse the summary or rely on aggregator caching)
            # For this MVP, let's rely on the aggregator running in 'execute_search' to populate the specific fields if possible?
            # Actually, _execute_search returns a string summary.
            # To get specific URLs into final_specs, we should probably do a "direct" search call in parallel if we want to retain the 'Agentic' benefit 
            # of deciding *what* to search, but typically for files/images we want the raw objects.
            
            # COMPROMISE for V1:
            # We let the Agent decide valid queries. 
            # We run the aggregator with those queries.
            # We collect the structured results from aggregator.
            # We let the LLM extract the "facts" (specs).
            # We aggregate appropriate URLs.

            # Re-running search to capture structured data (or optimize _execute_search to return it)
            # Let's simple capture what we can.
            
        # Post-loop formatted return
        # Map state.knowledge facts to specifications
        final_specs.specifications = state.knowledge
        
        # We need to make sure we return a robust result. 
        # Since the Agent loop above focused on "facts", we might consider running a final "standard" aggregator search 
        # to ensure we get the PDF/Image lists which are hard for the LLM to transcribe manually into JSON.
        # Or we can trust that the agent saw them.
        
        # Let's do a quick standard search to ensure we have the URLs (assets), 
        # while using the Agent's "knowledge" for the text specs.
        try:
           std_res = aggregator.search_machine_specs(machine_name, manufacturer)
           final_specs.datasheet_urls = std_res.datasheet_urls
           final_specs.image_urls = std_res.image_urls
           final_specs.sources = std_res.sources
           if not final_specs.manufacturer_website:
               final_specs.manufacturer_website = std_res.manufacturer_website
        except:
           pass

        return final_specs

    def search_suppliers_agentic(self, machine_name: str, machine_type: str = "", region: str = "Algeria") -> List[SupplierResult]:
        """
        Agentic loop to find suppliers.
        """
        initial_goal = f"Find active suppliers for '{machine_name}' ({machine_type}) that can ship to {region}. Need: price, contact info."
        state = AgentState(goal=initial_goal, missing=["supplier list", "prices", "contacts"])
        
        suppliers_found: List[SupplierResult] = []
        
        logger.info(f"START AGENTIC SEARCH SUPPLIERS: {machine_name}")

        for step in range(MAX_STEPS):
            # 1. PLAN
            prompt = PLANNER_PROMPT.format(
                goal=state.goal,
                step=step + 1,
                max_steps=MAX_STEPS,
                knowledge=json.dumps(state.knowledge, indent=2),
                missing=json.dumps(state.missing),
                history="\n".join(state.history)
            )
            plan = self._call_llm(prompt, f"plan_supp_step_{step}")
            
            # --- Robust Fallback Logic ---
            action = plan.get("action")
            queries = plan.get("search_queries", [])
            
            if not plan or not action:
                if step == 0:
                    logger.warning(f"Plan failed for {machine_name}, using fallback search strategy.")
                    action = "SEARCH"
                    queries = [
                        f"{machine_name} manufacturer",
                        f"{machine_name} OEM",
                        f"{machine_name} distributor Algeria",
                        f"{machine_name} distributor MENA",
                        f"{machine_name} supplier France"
                    ]
                else:
                    action = "FINISH"
            
            if action == "FINISH":
                break
                
            queries = plan.get("search_queries", [])
            if not queries:
                 queries = [f"buy {machine_name} {region}", f"{machine_name} suppliers {region}"]
            
            state.history.append(f"Step {step}: Searching {queries}")
            
            # 2. ACT: We need structured SupplierResults
            # We will try to map the agent's query to our aggregator
            for q in queries[:5]: # Hard limit to top 5 candidates
                # We use the query as the 'machine_name' param to the aggregator to force it to search that string
                # This leverages the existing multi-provider logic
                try:
                    res = aggregator.search_machine_suppliers(q, region=region, max_total_results=5)
                    logger.info(f"Query '{q}' returned {len(res)} results.")
                    suppliers_found.extend(res)
                except Exception as e:
                    logger.warning(f"Supplier search query '{q}' failed: {e}")
            
            # Dedupe
            unique = {}
            seen_count = len(suppliers_found)
            for s in suppliers_found:
                if s.supplier_name not in unique:
                    unique[s.supplier_name] = s
            suppliers_found = list(unique.values())
            logger.info(f"Total suppliers collected: {seen_count}, Unique after dedup: {len(suppliers_found)}")
            
            # 3. OBSERVE
            # We update knowledge with count of suppliers found
            state.knowledge["suppliers_count"] = len(suppliers_found)
            if len(suppliers_found) >= 5:
                # Good enough
                break
        
        # Post-process: enrich contacts
        logger.info(f"Enriching contacts for {len(suppliers_found)} found suppliers...")
        for s in suppliers_found:
            if not s.email_address or not s.phone_number:
                try:
                    c_info = aggregator.search_company_contacts(s.supplier_name, region)
                    if c_info:
                        if not s.email_address and c_info.get("email"):
                            s.email_address = c_info["email"]
                        if not s.phone_number and c_info.get("phone"):
                            s.phone_number = c_info["phone"]
                        if not s.website and c_info.get("website"):
                            s.website = c_info["website"]
                except Exception:
                    pass

        return suppliers_found

# Singleton instance
agentic_search = AgenticSearch()
