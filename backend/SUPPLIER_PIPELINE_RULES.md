# Supplier-Sourcing Pipeline Rules & Invariants

**Date**: 2025-01-30  
**Version**: 1.0  
**Owner**: Module 4 Enrichment Pipeline

---

## 📋 Overview

This document defines the **hardened rules and invariants** for the supplier-sourcing/enrichment pipeline in Module 4. All code changes must respect these rules to ensure **budget integrity**, **quality filtering**, and **transparent outcomes**.

---

## 🎯 Core Design Principles

1. **Bounded Execution**: Hard limits everywhere, no retries that multiply cost
2. **Explicit Outcomes**: Every machine gets a clear result (found/skipped/failed)
3. **Quality First**: Filter out irrelevant sources, require strong supplier signals
4. **Budget Integrity**: Consistent tracking and validation of web calls
5. **Transparency**: Log all filtering decisions

---

## 💰 Web Call Definition & Budget Tracking

### Definition: What Counts as a "Web Call"

A **web call** is any network operation to an external service:

| Operation | Counts as Web Call? | Category |
|-----------|-------------------|----------|
| Search API call (Serper, Bing, etc.) | ✅ YES | `search_query` |
| Page fetch/scrape for content | ✅ YES | `page_fetch` |
| Image search query | ✅ YES | `image_query` |
| Cache retrieval (no network) | ❌ NO | `cache_hit` (tracked separately) |

### Budget Hierarchy

```
Global Budget (all machines)
├── max_web_calls = machines_count × 2
└── Per-Machine Budget
    ├── max_queries = 1
    ├── max_pages = 6
    ├── max_llm_calls = 1
    └── timeout_seconds = 15
```

### Invariants

✅ **MUST**: `global_budget.web_calls_used ≤ global_budget.max_web_calls`  
✅ **MUST**: Each web operation is tracked via `WebCallTracker`  
✅ **MUST**: Budget summaries match actual network operations  
✅ **MUST**: Cache hits don't count toward budget

### Implementation

- **Budget Tracker**: [`backend/utils/module_4/budget_tracker.py`](backend/utils/module_4/budget_tracker.py)
- **Key Classes**:
  - `WebCallTracker`: Tracks all web operations with timestamps
  - `PerMachineBudget`: Per-machine limits and usage
  - `GlobalBudget`: Global coordination and validation

---

## 🎭 Supplier Outcome Tracking

### Invariant: Explicit Outcomes

**RULE**: Every machine **MUST** have exactly one explicit supplier outcome.

**No ambiguous states allowed**:
- ❌ Empty `suppliers: []` without explanation
- ❌ Undefined/null outcome
- ✅ Clear status + reason

### Outcome States

#### Success States
- `SUPPLIERS_FOUND`: Found ≥1 supplier after filtering

#### Skip States (Valid Reasons)
- `SKIPPED_NO_BUDGET`: Global budget exhausted
- `SKIPPED_GENERIC`: Generic/standard machine, no OEM needed
- `SKIPPED_BASIC`: Simple machine, local suppliers sufficient
- `SKIPPED_TIMEOUT`: Processing timed out before search

#### Failure States (Search Attempted)
- `SEARCH_FAILED_API_ERROR`: API/network error
- `SEARCH_FAILED_NO_RESULTS`: Search returned 0 results
- `SEARCH_FAILED_ALL_FILTERED`: All candidates filtered out (quality too low)
- `SEARCH_FAILED_TIMEOUT`: Search exceeded timeout
- `SEARCH_FAILED_EXCEPTION`: Unexpected exception

### Outcome Validation

**At pipeline end**:
```
outcome_registry.validate() → True if all machines have outcomes
```

If validation fails → **CRITICAL BUG** → Pipeline must not proceed

### Implementation

- **Outcome Tracker**: [`backend/utils/module_4/supplier_outcome.py`](backend/utils/module_4/supplier_outcome.py)
- **Key Classes**:
  - `SupplierOutcomeStatus`: Enum of all valid states
  - `SupplierOutcome`: Complete outcome record
  - `SupplierOutcomeRegistry`: Tracks all machines

---

## 🔍 Supplier Quality Filtering

### Problem Statement

Raw search results often contain **irrelevant sources**:
- Government/regulatory PDFs (`.gov.dz`, `.gov`, `.int`)
- Generic marketplaces (Alibaba, Amazon, eBay)
- Content farms and news articles
- PDF-only sources with no company identity

### Filtering Rules

#### Rejection Patterns (Auto-Reject)

1. **Government/Regulatory**:
   - `.gov.dz`, `.gov`, `.org`, `.int`, `europa.eu`
   - `douane`, `customs`, `ministere`, `regulation`

2. **Marketplaces**:
   - `alibaba.com`, `amazon.`, `ebay.`, `aliexpress`
   - `indiamart` (unless company page with verified identity)

3. **Content Sites**:
   - `wikipedia`, `youtube`, `linkedin/pulse`, `medium.com`
   - Generic directories without direct supplier info

4. **Generic PDFs**:
   - `.pdf` URLs without company identity
   - Datasheets from aggregators

#### Required Signals (Must Have ≥2 Categories)

1. **Company Identity** (40% weight):
   - Company name clearly stated
   - "About us" section
   - Corporate branding
   - Contact page

2. **Commercial** (30% weight):
   - Pricing information
   - Product catalogs
   - Sales contact
   - "Buy now" or quote request

3. **Product/Service** (20% weight):
   - Specific products listed
   - Technical specifications
   - Service offerings
   - Case studies

4. **Business Presence** (10% weight):
   - Physical address
   - Years in business
   - Certifications (ISO, CE)
   - Client testimonials

### Scoring Algorithm

```python
score = (
    company_identity_score * 0.4 +
    commercial_score * 0.3 +
    product_service_score * 0.2 +
    business_presence_score * 0.1
)

min_score_threshold = 0.5  # Require at least moderate quality
```

### Filtering Pipeline

1. **Check rejection patterns** → Auto-reject if match
2. **Extract signals** → Score each category
3. **Calculate weighted score** → Must be ≥ `min_score`
4. **Verify signal diversity** → Must have ≥2 categories with signals
5. **Log decision** → Record reason for keep/reject

### Implementation

- **Supplier Filter**: [`backend/utils/module_4/supplier_filter.py`](backend/utils/module_4/supplier_filter.py)
- **Key Functions**:
  - `filter_and_score_supplier()`: Score single supplier
  - `filter_suppliers()`: Filter list with logging
  - `deduplicate_suppliers()`: Remove duplicates

---

## 🔄 Integration Points

### Phase C: Web Validation (core_v2.py)

```python
# OLD: No filtering, ambiguous outcomes
results = aggregator.search_machine_suppliers(...)
suppliers = [extract_from_result(r) for r in results[:3]]

# NEW: With filtering + outcome tracking
raw_results = aggregator.search_machine_suppliers(...)
raw_suppliers = [convert_to_dict(r) for r in raw_results]

# Apply quality filtering
filtered_suppliers = filter_suppliers(
    suppliers=raw_suppliers,
    machine_name=original_name,
    machine_type=canonical_name,
    min_score=0.5
)

# Deduplicate
suppliers = deduplicate_suppliers(filtered_suppliers)[:3]

# Record explicit outcome
if suppliers:
    outcome_registry.record_success(...)
else:
    outcome_registry.record_failure(
        status=SupplierOutcomeStatus.SEARCH_FAILED_ALL_FILTERED,
        ...
    )
```

### Budget Integration

```python
# Create per-machine budget
machine_budget = global_budget.create_machine_budget(
    machine_name=nom_machine,
    max_queries=1,
    max_pages=6,
    max_llm_calls=1,
    timeout_seconds=15
)

# Track operations
machine_budget.record_query("aggregator", query)
machine_budget.record_page_fetch(url)

# Finalize (updates global)
global_budget.finalize_machine(nom_machine)
```

---

## 📊 Validation & Compliance

### At Pipeline Completion

**Budget Validation**:
```python
assert global_budget.web_calls_used <= global_budget.max_web_calls
global_budget.log_global_summary()
```

**Outcome Validation**:
```python
assert outcome_registry.validate()  # All machines have outcomes
outcome_registry.log_summary()
```

**Quality Metrics**:
- Candidates evaluated vs. filtered (logged)
- Average supplier score (logged)
- Rejection reasons (logged)

### Metadata in Output

```json
{
  "ribif_metadata": {
    "enrichment_method": "Module4 Bounded 4-Phase Pipeline with Quality Filtering",
    "web_calls_used": 75,
    "web_calls_budget": 80,
    "budget_compliant": true,
    "web_call_breakdown": "30 queries + 45 pages + 0 images = 75 total",
    "supplier_outcomes": {
      "total_machines": 40,
      "machines_with_outcome": 40,
      "success": 25,
      "skipped": 10,
      "failed": 5,
      "total_suppliers_found": 60,
      "all_machines_have_outcome": true
    }
  }
}
```

---

## 🚨 Critical Assertions

These assertions **MUST** pass or the pipeline fails:

1. **Budget**: `web_calls_used ≤ max_web_calls`
2. **Outcomes**: All machines have explicit outcome
3. **No Contact Enrichment**: No `email`/`phone` in Phase C suppliers
4. **Per-Machine Limits**: Each machine respects budgets
5. **Excluded Classes**: Subsystems never trigger web validation

---

## 🛠️ Code Structure

```
backend/utils/module_4/
├── core_v2.py              # Main pipeline (4 phases)
├── budget_tracker.py       # Budget tracking (NEW)
├── supplier_outcome.py     # Outcome tracking (NEW)
└── supplier_filter.py      # Quality filtering (NEW)

backend/utils/web_search/
├── aggregator.py           # Multi-provider search
├── sourcing_agent.py       # LLM-driven discovery
└── [providers...]          # Serper, Alibaba, etc.
```

---

## 📈 Monitoring & Debugging

### Logs to Watch

**Budget**:
```
[WEB CALL] Search query #1: aggregator - Plastic Injection Molding Machine
[WEB CALL] Page fetch #1: https://example.com/supplier
[CACHE HIT] #1: plastic_injection_molding_machine::suppliers_v1
```

**Filtering**:
```
[FILTER] Rejecting supplier 'XYZ': government website (.gov.dz)
[FILTER] Accepting supplier 'ABC Co': score=0.75 (company_identity=0.8, commercial=0.7)
[FILTER] Filtered out 7 candidates, kept 3
```

**Outcomes**:
```
✓ Supplier outcome for 'Machine A': SUPPLIERS_FOUND, 2 suppliers
⊘ Supplier outcome for 'Machine B': SKIPPED_GENERIC, subsystem
✗ Supplier outcome for 'Machine C': SEARCH_FAILED_ALL_FILTERED, 5 candidates filtered
```

---

## 🔗 Related Files

- **Budget Tracker**: [`budget_tracker.py`](backend/utils/module_4/budget_tracker.py)
- **Outcome Tracker**: [`supplier_outcome.py`](backend/utils/module_4/supplier_outcome.py)
- **Supplier Filter**: [`supplier_filter.py`](backend/utils/module_4/supplier_filter.py)
- **Main Pipeline**: [`core_v2.py`](backend/utils/module_4/core_v2.py)

---

## ✅ Checklist for PR Review

Before merging supplier pipeline changes:

- [ ] All web operations tracked via `WebCallTracker`
- [ ] Every machine has explicit `SupplierOutcome`
- [ ] Quality filtering applied with logged decisions
- [ ] Budget assertions pass
- [ ] Outcome validation passes
- [ ] No contact enrichment in Phase C
- [ ] Metadata includes budget + outcome summaries
- [ ] Logs show detailed breakdown

---

**Document Owner**: Module 4 Team  
**Last Updated**: 2025-01-30  
**Next Review**: When making structural changes to supplier pipeline
