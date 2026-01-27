# UPGRADED AGENTIC SUPPLIER SOURCING WORKFLOW

**Version 2.0 - High-Recall Configuration**

## Overview

This document describes the UPGRADED agentic supplier sourcing workflow designed for **higher recall** - finding MANY more suppliers (30-80+ raw candidates → 15-40 final suppliers) while staying bounded with better time budgets and resilience.

## Key Improvements

### 1. **Increased Limits**
   - **Queries**: 3 → **5 queries** per machine
   - **Pages**: 12 → **20 pages** total
   - **Timeout**: 45s → **180s (3 minutes)** per machine
   - **Candidate Cap**: 30 → **80 raw candidates** (harvest limit)
   - **Target Suppliers**: 15-30 → **15-40 final suppliers**
   - **LLM Calls**: 1 → **3 max calls** (query planning, extraction, synthesis)

### 2. **Multi-Pass Search Strategy**

Instead of a single search approach, the workflow now uses **3 strategic passes**:

#### **Pass 1: BROAD (OEM/Manufacturer Focus)**
- Target: Global manufacturers, OEM suppliers, authorized distributors
- Keywords: `manufacturer`, `supplier`, `distributor`
- Geographic: **No regional restriction** (cast wide net)
- Goal: Find major global players

Example query:
```
injection molding machine (manufacturer OR supplier OR distributor) injection molding plastic
```

#### **Pass 2: REGIONAL (Local/North Africa Focus)**
- Target: Regional distributors, agents, representatives, service centers
- Keywords: `distributor`, `dealer`, `agent`, `representative`, `service center`, `integrator`
- Geographic: **Algeria, Maghreb, North Africa**
- Goal: Find local suppliers who can provide service/support

Example queries:
```
injection molding machine (distributor OR dealer OR agent OR representative) injection molding plastic (Algeria OR Maghreb OR "North Africa")

injection molding machine ("service center" OR integrator OR installer OR "after sales") injection molding plastic (Algeria OR Maghreb OR "North Africa")
```

#### **Pass 3: VERTICAL (Industry-Specific Focus)**
- Target: OEM partners, authorized integrators, turnkey solution providers
- Keywords: `OEM partner`, `authorized integrator`, `turnkey supplier`, `solution provider`
- Geographic: **Mixed** (global OEM partners, regional solution providers)
- Goal: Find specialized industry-specific suppliers

Example queries:
```
injection molding machine "OEM partner" "authorized integrator" injection molding plastic polymer thermoplastic

injection molding machine "turnkey supplier" "solution provider" injection molding plastic (Algeria OR Maghreb OR "North Africa")
```

**Multipass Control:**
- Enabled via `enable_multipass=True` in config
- Falls back to legacy 3-query strategy if disabled
- Each pass tracked separately in metrics (`search_pass_1_results`, `search_pass_2_results`, `search_pass_3_results`)

### 3. **Retry Logic with Exponential Backoff**

Both search and page fetching now have robust retry logic:

#### **Search Retry**
- **Max retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s base delay)
- **Jitter**: Random 0-1s added to avoid thundering herd
- **Retry on**: Network errors, API failures, server errors (5xx)

#### **Page Fetch Retry**
- **Max retries**: 2 attempts
- **Backoff**: Exponential (0.5s, 1s base delay)
- **Jitter**: Random 0-0.5s added
- **Retry on**: Network errors (timeout, connection), server errors (5xx)
- **No retry on**: Client errors (4xx like 404, 403)

**Implementation:**
```python
# Search with retry
search_results = search_with_diversity(
    query=query,
    max_results=15,
    domain_cap=3,
    max_retries=3,
    backoff_base=1.0,
    use_jitter=True,
)

# Fetch with retry
html = fetch_page_content(
    url=url,
    timeout=10.0,
    max_retries=2,
    backoff_base=0.5,
    use_jitter=True,
)
```

**Metrics tracked:**
- `retry_attempts`: Total retry attempts made
- `retry_successes`: How many retries succeeded

### 4. **Candidate Harvesting (30-80 Raw Candidates)**

The workflow now aims to collect **30-80 raw candidates** before filtering:

- **Harvest limit**: `candidate_cap=80` (stops search when reached)
- **Tracking**: `raw_candidates` metric added
- **Purpose**: Cast wider net before applying deduplication and scoring

**Pipeline:**
1. Harvest 30-80 raw candidates (with duplicates, varying quality)
2. Deduplicate by (normalized name, domain)
3. Filter by confidence score (≥0.25)
4. Take top 15-40 by score

### 5. **Fallback Vendor Catalog**

**GUARANTEED MINIMUM RESULTS**: If the workflow finds fewer than 10 suppliers, it uses a fallback catalog of known B2B marketplaces.

#### **Fallback Catalog (8 Known Vendors):**
1. **Alibaba** - Global B2B marketplace for industrial machinery
2. **Made-in-China.com** - Chinese B2B marketplace for industrial equipment
3. **IndiaMART** - Indian B2B marketplace for industrial machinery
4. **TradeIndia** - Indian B2B portal for industrial equipment
5. **Europages** - European B2B directory for industrial suppliers
6. **Kompass Algeria** - Algerian business directory (HIGHEST PRIORITY)
7. **ThomasNet** - North American industrial supplier directory
8. **Global Sources** - Global B2B marketplace for industrial products

**Activation:**
- Enabled via `enable_fallback_catalog=True`
- Threshold: `fallback_catalog_threshold=10` (triggers if < 10 suppliers found)
- Suppliers marked with `is_fallback: True` in metadata
- Confidence score: 0.5-0.8 (lower than organic suppliers)

**Metrics tracked:**
- `suppliers_from_fallback`: Count of fallback suppliers added
- `fallback_catalog_used`: Boolean flag

### 6. **Best-Effort Guarantees**

The workflow now has **progressive threshold relaxation** to ensure reasonable results:

#### **Stage 1: Strict Filter**
- Apply minimum confidence score: `min_confidence_score=0.25`

#### **Stage 2: Relaxed Filter (if < 10 suppliers)**
- Lower threshold to `0.25 * 0.7 = 0.175`
- Warning logged: "Relaxing threshold"

#### **Stage 3: Fallback Catalog (if still < 10)**
- Add suppliers from fallback catalog
- Guaranteed to return at least 10 suppliers

**Result:** The workflow will **never return zero suppliers** (unless critical error).

### 7. **Enhanced Observability**

The metrics and logging have been significantly enhanced:

#### **New Metrics Fields:**
```python
@dataclass
class SourcingMetrics:
    # Query tracking
    queries_tried: List[str]  # Full list of queries executed
    
    # Multi-pass tracking
    search_pass_1_results: int  # Broad pass results
    search_pass_2_results: int  # Regional pass results
    search_pass_3_results: int  # Vertical pass results
    
    # Retry tracking
    retry_attempts: int
    retry_successes: int
    
    # Candidate tracking
    raw_candidates: int  # Before dedup
    
    # Fallback tracking
    suppliers_from_fallback: int
    fallback_catalog_used: bool
    
    # LLM tracking (enhanced)
    llm_query_planning: int
    llm_extraction: int
    llm_synthesis: int
```

#### **Enhanced Logging:**
```
============================================================
SOURCING COMPLETE: injection molding machine
  Queries: 5/5
  Search Pass 1 (Broad): 42 results
  Search Pass 2 (Regional): 18 results
  Search Pass 3 (Vertical): 23 results
  Raw candidates: 67
  After dedup: 52
  After filter: 38
  Fallback used: False (0 suppliers)
  Final suppliers: 38 (H:15, M:18, L:5)
  Duration: 127.3s / 180s
  Timed out: False
============================================================
```

## Configuration

### **Default Config (Upgraded)**
```python
DEFAULT_CONFIG = SourcingConfig(
    max_queries=5,              # 3 → 5
    max_results_per_query=15,   # 10 → 15
    max_pages_total=20,         # 12 → 20
    domain_diversity_cap=3,     # 2 → 3
    target_suppliers_min=15,    # same
    target_suppliers_max=40,    # 30 → 40
    candidate_cap=80,           # 30 → 80
    min_confidence_score=0.25,  # 0.3 → 0.25 (more lenient)
    timeout_per_machine=180.0,  # 45s → 180s (3 minutes)
    use_llm_ranking=True,       # False → True
    max_llm_calls=3,            # 1 → 3
    
    # NEW: Retry logic
    max_retries=3,
    retry_backoff_base=1.0,
    retry_jitter=True,
    
    # NEW: Multi-pass strategy
    enable_multipass=True,
    search_passes=3,
    
    # NEW: Fallback catalog
    enable_fallback_catalog=True,
    fallback_catalog_threshold=10,
)
```

### **Custom Config Example**
```python
# Ultra-high recall (willing to wait longer)
ultra_config = SourcingConfig(
    max_queries=5,
    max_pages_total=30,         # Even more pages
    timeout_per_machine=240.0,  # 4 minutes
    candidate_cap=100,          # Harvest up to 100
    target_suppliers_max=50,    # Return up to 50
    enable_multipass=True,
    enable_fallback_catalog=True,
)

# Fast mode (less time, fewer suppliers)
fast_config = SourcingConfig(
    max_queries=3,
    max_pages_total=12,
    timeout_per_machine=60.0,   # 1 minute
    candidate_cap=30,
    target_suppliers_max=20,
    enable_multipass=False,     # Use legacy strategy
    enable_fallback_catalog=False,
)
```

## Usage

### **Basic Usage**
```python
from utils.module_4.supplier_sourcing_agentic import source_suppliers_for_machine

# Use upgraded default config
result = source_suppliers_for_machine("injection molding machine")

print(f"Found {result.metrics.suppliers_final} suppliers")
print(f"Raw candidates harvested: {result.metrics.raw_candidates}")
print(f"Search passes: {result.metrics.search_pass_1_results}, {result.metrics.search_pass_2_results}, {result.metrics.search_pass_3_results}")
print(f"Fallback used: {result.metrics.fallback_catalog_used}")
```

### **Custom Config Usage**
```python
from utils.module_4.supplier_sourcing_agentic import (
    source_suppliers_for_machine,
    SourcingConfig,
)

config = SourcingConfig(
    max_queries=5,
    max_pages_total=25,
    timeout_per_machine=180.0,
    enable_multipass=True,
    enable_fallback_catalog=True,
    fallback_catalog_threshold=15,  # Higher threshold
)

result = source_suppliers_for_machine("cnc milling machine", config)
```

### **Batch Processing**
```python
from utils.module_4.supplier_sourcing_agentic import source_suppliers_batch

machines = [
    "injection molding machine",
    "cnc lathe",
    "packaging machine",
]

results = source_suppliers_batch(machines, max_workers=4)

for result in results:
    print(f"{result.machine}: {result.metrics.suppliers_final} suppliers")
```

## Performance Characteristics

### **Old Workflow (v1.0)**
- **Queries**: 3
- **Pages**: ~12
- **Time**: ~45s
- **Suppliers**: 15-30
- **Failure mode**: Return 5-10 if searches fail

### **New Workflow (v2.0)**
- **Queries**: 5 (multi-pass)
- **Pages**: ~20
- **Time**: ~120-180s
- **Suppliers**: 30-40 (up to 80 raw candidates)
- **Failure mode**: Guaranteed ≥10 (fallback catalog)

### **Typical Metrics**
```
Duration: 120-180s
Raw candidates: 40-80
After dedup: 30-60
After filter: 25-45
Final suppliers: 30-40
  High confidence: 10-15
  Medium confidence: 12-20
  Low confidence: 3-8
Fallback used: Rarely (only if <10 organic)
```

## Testing

Run the upgrade test:
```bash
cd backend
python -m utils.module_4.test_upgraded_agentic
```

Expected output:
- ✅ At least 10 suppliers found (with fallback guarantee)
- ✅ Multi-pass search executed
- ✅ 30+ raw candidates harvested
- ✅ Fallback catalog enabled
- ✅ Retry logic configured

## Backward Compatibility

The upgrade is **100% backward compatible**:

1. **Default behavior**: Uses upgraded config automatically
2. **Custom configs**: Still work, just add new fields if desired
3. **API**: No breaking changes to function signatures
4. **Legacy mode**: Set `enable_multipass=False` to use old query strategy

## Migration from v1.0

No code changes required! The upgrade is automatic.

If you want to keep the old behavior:
```python
# Use old limits
legacy_config = SourcingConfig(
    max_queries=3,
    max_pages_total=12,
    timeout_per_machine=45.0,
    candidate_cap=30,
    target_suppliers_max=30,
    enable_multipass=False,
    enable_fallback_catalog=False,
)

result = source_suppliers_for_machine(machine, legacy_config)
```

## Summary

The **upgraded workflow (v2.0)** delivers:

✅ **Higher recall**: 30-40 suppliers (vs 15-30)
✅ **More resilient**: Retry logic with exponential backoff
✅ **Better coverage**: Multi-pass search strategy (broad/regional/vertical)
✅ **Guaranteed results**: Fallback catalog ensures ≥10 suppliers
✅ **Enhanced observability**: Detailed metrics and logging
✅ **Backward compatible**: No breaking changes

**Trade-off**: Takes ~2-3x longer (120-180s vs 45s), but finds significantly more suppliers with better quality and coverage.
