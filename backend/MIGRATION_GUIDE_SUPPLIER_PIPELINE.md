# Migration Guide: Old → New Supplier Pipeline

**For**: Developers updating code that uses the supplier-sourcing pipeline  
**Version**: 1.0 (2025-01-30)

---

## 🔄 Overview of Changes

The supplier-sourcing pipeline has been **hardened** with three new systems:

1. **Budget Tracking** (`budget_tracker.py`) - Clear web call definitions + consistent tracking
2. **Outcome Tracking** (`supplier_outcome.py`) - Explicit outcomes for every machine
3. **Quality Filtering** (`supplier_filter.py`) - Filter irrelevant sources, score suppliers

---

## 📝 Breaking Changes

### 1. Function Signatures Changed

#### `web_validate_minimal()`

**OLD**:
```python
def web_validate_minimal(
    canonical_name: str,
    original_name: str,
    budget: WebValidationBudget  # Old budget class
) -> Dict[str, Any]:
```

**NEW**:
```python
def web_validate_minimal(
    canonical_name: str,
    original_name: str,
    budget: PerMachineBudget,        # NEW: From budget_tracker.py
    outcome_registry: SupplierOutcomeRegistry  # NEW: Required
) -> Dict[str, Any]:
```

#### `enrich_machine_bounded()`

**OLD**:
```python
def enrich_machine_bounded(
    machine: Dict[str, Any],
    global_budget: GlobalBudget  # Old simple class
) -> Optional[Dict[str, Any]]:
```

**NEW**:
```python
def enrich_machine_bounded(
    machine: Dict[str, Any],
    global_budget: GlobalBudget,           # NEW: From budget_tracker.py
    outcome_registry: SupplierOutcomeRegistry  # NEW: Required
) -> Optional[Dict[str, Any]]:
```

#### `process_module_4_bounded()`

**No signature change**, but now creates and validates:
- `GlobalBudget` (from `budget_tracker.py`)
- `SupplierOutcomeRegistry` (from `supplier_outcome.py`)

---

## 🔧 How to Migrate Your Code

### If You Call `process_module_4_bounded()` Directly

**No changes required!** The function handles everything internally.

```python
# This still works exactly the same
from utils.module_4.core_v2 import process_module_4_bounded

result = process_module_4_bounded(machines, max_workers=8)
```

### If You Call `enrich_machine_bounded()` Directly

**You must now**:
1. Create `GlobalBudget` from `budget_tracker.py`
2. Create `SupplierOutcomeRegistry`
3. Pass both to the function

**OLD**:
```python
from utils.module_4.core_v2 import enrich_machine_bounded, GlobalBudget

global_budget = GlobalBudget(
    total_machines=10,
    max_web_calls=20
)

result = enrich_machine_bounded(machine, global_budget)
```

**NEW**:
```python
from utils.module_4.core_v2 import enrich_machine_bounded
from utils.module_4.budget_tracker import GlobalBudget
from utils.module_4.supplier_outcome import SupplierOutcomeRegistry

global_budget = GlobalBudget(
    max_web_calls=20,
    machines_count=10
)
outcome_registry = SupplierOutcomeRegistry(total_machines=10)

result = enrich_machine_bounded(machine, global_budget, outcome_registry)
```

### If You Call `web_validate_minimal()` Directly

**You must now**:
1. Use `PerMachineBudget` instead of `WebValidationBudget`
2. Pass `SupplierOutcomeRegistry`

**OLD**:
```python
from utils.module_4.core_v2 import web_validate_minimal, WebValidationBudget

budget = WebValidationBudget(start_time=time.time())
result = web_validate_minimal(canonical_name, original_name, budget)
```

**NEW**:
```python
from utils.module_4.core_v2 import web_validate_minimal
from utils.module_4.budget_tracker import GlobalBudget, PerMachineBudget
from utils.module_4.supplier_outcome import SupplierOutcomeRegistry

# Create global context
global_budget = GlobalBudget(max_web_calls=100, machines_count=50)
outcome_registry = SupplierOutcomeRegistry(total_machines=50)

# Create per-machine budget
machine_budget = global_budget.create_machine_budget(
    machine_name="Machine A",
    max_queries=1,
    max_pages=6,
    max_llm_calls=1,
    timeout_seconds=15
)

# Call function
result = web_validate_minimal(
    canonical_name,
    original_name,
    machine_budget,
    outcome_registry
)

# Finalize budget
global_budget.finalize_machine("Machine A")
```

---

## 🆕 New Behavior

### 1. Supplier Filtering Applied Automatically

**Before**: Raw search results returned as-is  
**After**: Results filtered to remove irrelevant sources

**Impact**: You may see fewer suppliers, but higher quality

**Example**:
```
Before: 10 results → 10 suppliers (includes gov PDFs, marketplaces)
After:  10 results → 3 suppliers (filtered to real companies)
```

### 2. Explicit Outcomes Required

**Before**: Empty suppliers with no explanation  
**After**: Every machine has explicit outcome (found/skipped/failed)

**Impact**: You can now distinguish between:
- "No suppliers found" (searched but 0 results)
- "Search skipped" (valid reason not to search)
- "All filtered" (found candidates but quality too low)

**Example**:
```json
{
  "machine_name": "AGV",
  "status": "skipped_generic",
  "reason": "Optional system - not priority for sourcing",
  "suppliers": []
}
```

### 3. Budget Tracking More Detailed

**Before**: Single counter for "web calls"  
**After**: Broken down into queries, pages, images, cache hits

**Impact**: More transparent budget usage in logs and metadata

**Example**:
```
Before: "Web calls: 45/80"
After:  "30 queries + 45 pages + 0 images = 75 total (5 cache hits)"
```

---

## 📊 Metadata Changes

### New Fields in `ribif_metadata`

```json
{
  "ribif_metadata": {
    // NEW: Detailed web call breakdown
    "web_call_breakdown": "30 queries + 45 pages + 0 images = 75 total",
    
    // NEW: Supplier outcome summary
    "supplier_outcomes": {
      "total_machines": 40,
      "machines_with_outcome": 40,
      "machines_missing_outcome": 0,
      "success": 25,
      "skipped": 10,
      "failed": 5,
      "total_suppliers_found": 60,
      "all_machines_have_outcome": true
    },
    
    // UPDATED: More descriptive method name
    "enrichment_method": "Module4 Bounded 4-Phase Pipeline with Quality Filtering"
  }
}
```

### Accessing Outcome Details

**NEW**: Each machine result now has outcome metadata in Phase C:

```json
{
  "machine_input": { ... },
  "suppliers": [...],
  
  // NEW: Available in phase_c dict if you access it
  "candidates_evaluated": 10,
  "candidates_filtered": 7,
  "web_source": "aggregator"
}
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Import Errors

**Error**:
```
ImportError: cannot import name 'WebValidationBudget' from 'utils.module_4.core_v2'
```

**Solution**:
`WebValidationBudget` removed. Use `PerMachineBudget` from `budget_tracker.py`:
```python
from utils.module_4.budget_tracker import PerMachineBudget
```

### Issue 2: Missing `outcome_registry` Parameter

**Error**:
```
TypeError: web_validate_minimal() missing 1 required positional argument: 'outcome_registry'
```

**Solution**:
Create and pass `SupplierOutcomeRegistry`:
```python
from utils.module_4.supplier_outcome import SupplierOutcomeRegistry

outcome_registry = SupplierOutcomeRegistry(total_machines=len(machines))
```

### Issue 3: GlobalBudget Constructor Changed

**Error**:
```
TypeError: __init__() got an unexpected keyword argument 'total_machines'
```

**Solution**:
New `GlobalBudget` uses different parameters:
```python
# OLD
GlobalBudget(total_machines=40, max_web_calls=80)

# NEW
GlobalBudget(max_web_calls=80, machines_count=40)
```

---

## ✅ Testing Your Migration

### 1. Run a Small Test

```python
from utils.module_4.core_v2 import process_module_4_bounded

# Test with 1-2 machines first
test_machines = [
    {"nom_machine": "Test Machine", "type": "Injection Molding"}
]

result = process_module_4_bounded(test_machines, max_workers=1)

# Check new metadata fields exist
assert "web_call_breakdown" in result["ribif_metadata"]
assert "supplier_outcomes" in result["ribif_metadata"]
assert result["ribif_metadata"]["supplier_outcomes"]["all_machines_have_outcome"]
```

### 2. Check Logs

Look for new log patterns:
```
[WEB CALL] Search query #1: ...
[WEB CALL] Page fetch #1: ...
[FILTER] Rejecting supplier '...': ...
[FILTER] Accepting supplier '...': score=0.75
✓ Supplier outcome for '...': SUPPLIERS_FOUND
```

### 3. Validate Assertions Pass

If any assertion fails, the pipeline will raise an error:
```
AssertionError: Global web budget exceeded: 85/80
AssertionError: Some machines missing explicit supplier outcome!
```

---

## 📚 Reference

### New Files to Review

1. [`budget_tracker.py`](backend/utils/module_4/budget_tracker.py) - Budget tracking system
2. [`supplier_outcome.py`](backend/utils/module_4/supplier_outcome.py) - Outcome tracking
3. [`supplier_filter.py`](backend/utils/module_4/supplier_filter.py) - Quality filtering
4. [`SUPPLIER_PIPELINE_RULES.md`](backend/SUPPLIER_PIPELINE_RULES.md) - Complete rules
5. [`SUPPLIER_PIPELINE_IMPLEMENTATION_SUMMARY.md`](backend/SUPPLIER_PIPELINE_IMPLEMENTATION_SUMMARY.md) - Summary

### Key Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `GlobalBudget` | `budget_tracker` | Global budget coordination |
| `PerMachineBudget` | `budget_tracker` | Per-machine budget tracking |
| `WebCallTracker` | `budget_tracker` | Track individual web operations |
| `SupplierOutcomeRegistry` | `supplier_outcome` | Track all machine outcomes |
| `SupplierOutcomeStatus` | `supplier_outcome` | Enum of valid outcome states |

---

## 🆘 Need Help?

### Common Questions

**Q**: Do I need to change my code if I only call `process_module_4_bounded()`?  
**A**: No! Top-level API unchanged.

**Q**: My supplier count decreased after migration. Is this a bug?  
**A**: No - quality filtering is working. Check logs for `[FILTER]` messages to see what was rejected.

**Q**: How do I disable filtering temporarily?  
**A**: In `core_v2.py`, change `min_score=0.5` to `min_score=0.0` in the `filter_suppliers()` call.

**Q**: Can I use the old `WebValidationBudget`?  
**A**: No, it's removed. Use `PerMachineBudget` from `budget_tracker.py`.

### Support

- See [`SUPPLIER_PIPELINE_RULES.md`](backend/SUPPLIER_PIPELINE_RULES.md) for complete rules
- Check [`SUPPLIER_PIPELINE_IMPLEMENTATION_SUMMARY.md`](backend/SUPPLIER_PIPELINE_IMPLEMENTATION_SUMMARY.md) for examples
- Review code comments in new files for implementation details

---

**Migration Guide Version**: 1.0  
**Last Updated**: 2025-01-30  
**Applicable to**: Module 4 supplier-sourcing pipeline
