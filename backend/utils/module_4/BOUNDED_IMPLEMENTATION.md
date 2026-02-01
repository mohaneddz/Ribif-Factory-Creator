# Module 4 Bounded Refactor - Implementation Summary

## Completed Implementation

### ✓ All Required Aspects Covered:

#### 1. **Phase A — Canonicalize + Classify (NO WEB)** ✓
- Canonical mapping for 25+ machines (merge synonyms)
- Classification into 4 classes:
  - `core_stable`: Well-known machines (injection, extrusion, thermoforming)
  - `core_variable`: Core but variable specs (robots, presses, mixers)
  - `optional_system`: Not critical (AGV, ASRS, packaging)
  - `subsystem_qc_utility`: EXCLUDED (vision, conveyors, silos, sensors)
- Confidence levels: high/medium/low
- **Subsystems automatically excluded from enrichment**

#### 2. **Phase B — Industry Grounding (NO WEB, deterministic)** ✓
- Knowledge base with 11 machine types
- Structured outputs (no long prose):
  - `role`: 1 sentence
  - `typical_capacity_range`: one line
  - `typical_power_range`: one line
  - `typical_footprint_range`: one line
  - `typical_manufacturers`: 3-5 names
- Disk caching with 7-day TTL
- Returns minimal safe object for unknown machines

#### 3. **Phase C — Minimal Web Validation (OPTIONAL, bounded)** ✓
- Only runs if: `machine_class == core_variable` OR `confidence == low`
- Hard budgets enforced per machine:
  - `max_search_queries_per_machine = 1`
  - `max_results_per_query = 5`
  - `max_fetch_pages_total = 6`
  - `max_llm_calls_total = 1` (synthesis only)
  - `max_runtime_per_machine = 15s`
- Extracts up to 3 supplier names + domains only
- **NO contact enrichment (no emails/phones)**
- Falls back gracefully on timeout/failure
- Disk caching with 7-day TTL

#### 4. **Phase D — Single Synthesis (ONE LLM CALL MAX)** ✓
- Merges Phase B + C in one LLM call
- Strict JSON schema validation
- **NO RETRY LOOPS on parse failure**
- Returns safe minimal object with `confidence="low"` on failure

#### 5. **Global Budget Enforcement** ✓
- `total_web_calls <= machines_count * 2`
- Global request counter tracks all web calls
- Prevents unbounded agentic loops

#### 6. **Caching System** ✓
- Cache keys: `specs::<canonical_name>::v1` and `suppliers::<canonical_name>::v1`
- 7-day TTL (configurable)
- MD5 hashed filenames in `cache/module_4/`

#### 7. **Runtime Assertions (unit-test-like checks)** ✓
- Per-machine budgets enforced (assertions in code)
- No contacts enrichment called (assertions verify)
- Excluded classes never trigger web (assertions check)
- Global budget compliance validated

#### 8. **Output Schema (strict)** ✓
```json
{
  "canonical_name": "string",
  "machine_class": "core_stable|core_variable|optional_system",
  "role": "string|null",
  "typical_capacity_range": "string|null",
  "typical_power_range": "string|null",
  "typical_footprint_range": "string|null",
  "typical_manufacturers": ["string"],
  "validated_suppliers": [
    {"name": "string", "domain": "string|null", "note": "string|null"}
  ],
  "confidence": "high|medium|low",
  "notes": "string|null"
}
```

#### 9. **Acceptance Criteria** ✓
For 40 inputs:
- ≤ 80 total web calls (40 * 2)
- ≤ 40 LLM calls (1 per machine for synthesis)
- Predictable runtime (~10-15 minutes for 40 machines)
- Stable, concise JSON output
- No supplier inflation

## Files Created/Modified:

1. **`backend/utils/module_4/core_v2.py`** (NEW, 960 lines)
   - Complete 4-phase pipeline implementation
   - All budgets and caching
   - Runtime assertions
   - Global budget tracker

2. **`backend/utils/web_search/search_bounded.py`** (NEW, 38 lines)
   - Single-shot search helper
   - NO agentic loops

3. **`backend/routes/module4.py`** (MODIFIED)
   - Updated to use `core_v2.process_module_4_bounded()`
   - Simplified DB sync for bounded output schema

4. **`backend/utils/web_search/__init__.py`** (MODIFIED)
   - Added import for `search_bounded`

5. **`backend/utils/module_4/test_bounded.py`** (NEW, 221 lines)
   - Comprehensive validation tests
   - Tests all phases
   - Validates budgets and acceptance criteria

## Key Design Decisions:

1. **Deterministic Industry Knowledge First** - Prefer stable priors over web
2. **Selective Web Usage** - Only for variable machines or low confidence
3. **Hard Caps Everywhere** - No unbounded loops or retries
4. **Safe Fallbacks** - Always return valid JSON, never crash
5. **Transparent Budgets** - All limits are constants at top of file
6. **Observable Performance** - Comprehensive logging of all phases

## Testing:

Run validation tests:
```bash
python -m backend.utils.module_4.test_bounded
```

## Expected Performance (40 machines):
- Total runtime: ~5-10 minutes
- Web calls: ≤ 80
- LLM calls: ≤ 40
- Output: Stable, concise JSON
- Cache hits reduce both significantly on subsequent runs
