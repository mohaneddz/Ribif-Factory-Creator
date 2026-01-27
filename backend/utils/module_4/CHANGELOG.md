# Changelog - Agentic Supplier Sourcing Workflow

## [2.0.0] - 2024 - HIGH-RECALL UPGRADE

### Added

#### Multi-Pass Search Strategy
- **3-pass search strategy**: Broad (OEM) → Regional (Algeria/Maghreb) → Vertical (Industry-specific)
- `enable_multipass` config flag to enable/disable
- `search_passes` config to control number of passes
- Per-pass result tracking in metrics (`search_pass_1_results`, `search_pass_2_results`, `search_pass_3_results`)

#### Retry Logic with Exponential Backoff
- Retry logic for `search_with_diversity()` function
  - Max retries: 3 attempts
  - Exponential backoff: 1s, 2s, 4s base delay
  - Random jitter: 0-1s to avoid thundering herd
- Retry logic for `fetch_page_content()` function
  - Max retries: 2 attempts
  - Exponential backoff: 0.5s, 1s base delay
  - Random jitter: 0-0.5s
  - Smart retry: no retry on 4xx client errors
- Config parameters: `max_retries`, `retry_backoff_base`, `retry_jitter`
- Metrics tracking: `retry_attempts`, `retry_successes`

#### Fallback Vendor Catalog
- 8 known B2B marketplaces as fallback suppliers
  - Alibaba, Made-in-China, IndiaMART, TradeIndia
  - Europages, Kompass Algeria, ThomasNet, Global Sources
- `get_fallback_suppliers()` function
- Config parameters: `enable_fallback_catalog`, `fallback_catalog_threshold`
- Triggered when organic results < threshold (default: 10)
- Metrics tracking: `suppliers_from_fallback`, `fallback_catalog_used`
- Suppliers marked with `is_fallback: True` in metadata

#### Enhanced Candidate Harvesting
- Increased candidate cap: 30 → 80 raw candidates
- `raw_candidates` metric to track harvest size
- Candidate cap enforced during search to prevent over-fetching

#### Best-Effort Guarantees
- Progressive threshold relaxation (0.25 → 0.175 if < 10 suppliers)
- Fallback catalog activation for guaranteed minimum results
- Never returns zero suppliers (unless critical error)

#### Enhanced Observability
- **New metrics fields:**
  - `queries_tried`: List of all queries executed
  - `search_pass_1/2/3_results`: Per-pass result counts
  - `raw_candidates`: Count before deduplication
  - `retry_attempts`, `retry_successes`: Retry statistics
  - `suppliers_from_fallback`: Fallback supplier count
  - `fallback_catalog_used`: Boolean flag
  - `llm_query_planning`, `llm_extraction`, `llm_synthesis`: LLM usage breakdown
- **Enhanced logging:**
  - Detailed summary log at workflow completion
  - Per-pass progress logging
  - Retry attempt logging
  - Fallback activation logging

#### Documentation
- `UPGRADE_GUIDE.md`: Comprehensive upgrade documentation
- `UPGRADE_SUMMARY.md`: Quick summary of changes
- `test_upgraded_agentic.py`: Test script for upgraded features
- `CHANGELOG.md`: This file

### Changed

#### Configuration Limits (Higher Recall)
- `max_queries`: 3 → **5** (+67%)
- `max_results_per_query`: 10 → **15** (+50%)
- `max_pages_total`: 12 → **20** (+67%)
- `domain_diversity_cap`: 2 → **3** (+50%)
- `target_suppliers_max`: 30 → **40** (+33%)
- `candidate_cap`: 30 → **80** (+167%)
- `min_confidence_score`: 0.3 → **0.25** (-17%, more lenient)
- `timeout_per_machine`: 45s → **180s** (+300%, 3 minutes)
- `timeout_per_page_fetch`: 10s → **12s** (+20%)
- `use_llm_ranking`: False → **True** (enabled by default)
- `max_llm_calls`: 1 → **3** (+200%)

#### Query Generation (`generate_query_variants`)
- Refactored to support multi-pass strategy
- Pass 1: Broad OEM/manufacturer queries (no regional restriction)
- Pass 2: Regional distributor/agent queries (Algeria/Maghreb focus)
- Pass 3: Vertical industry-specific queries (OEM partners, turnkey)
- Falls back to legacy 3-query strategy if `enable_multipass=False`

#### Search Execution (`search_with_diversity`)
- Added retry parameters: `max_retries`, `backoff_base`, `use_jitter`
- Implements exponential backoff with optional jitter
- Returns empty list after max retries (instead of throwing exception)

#### Page Fetching (`fetch_page_content`)
- Added retry parameters: `max_retries`, `backoff_base`, `use_jitter`
- Implements exponential backoff with optional jitter
- Smart retry: skips retry on 4xx client errors
- Returns `None` after max retries

#### Main Workflow (`source_suppliers_for_machine`)
- Integrated multi-pass search execution
- Added pass-specific metrics tracking
- Candidate cap enforcement during search loop
- Integrated fallback catalog invocation
- Progressive threshold relaxation logic
- Enhanced summary logging at completion

### Performance Impact

**Execution Time:**
- Old: ~45s per machine
- New: ~120-180s per machine (2-3x longer)

**API Calls:**
- Old: 3 queries, ~12 pages
- New: 5 queries, ~20 pages (~67% more)

**Results:**
- Old: 15-30 suppliers (typical)
- New: 30-40 suppliers (typical), guaranteed ≥10

**Quality:**
- Higher recall: More suppliers found
- Better coverage: Multi-pass strategy finds regional + OEM + vertical suppliers
- Guaranteed minimum: Never returns zero due to fallback catalog

### Backward Compatibility

✅ **100% backward compatible**
- Existing code works without changes
- Default config automatically uses upgraded limits
- No breaking API changes
- Legacy mode available via `enable_multipass=False`

### Migration Guide

**No code changes required!** The upgrade is automatic.

If you want legacy behavior:
```python
legacy_config = SourcingConfig(
    max_queries=3,
    max_pages_total=12,
    timeout_per_machine=45.0,
    enable_multipass=False,
    enable_fallback_catalog=False,
)
result = source_suppliers_for_machine(machine, legacy_config)
```

### Testing

Run test suite:
```bash
cd backend
python -m utils.module_4.test_upgraded_agentic
```

Expected:
- ✅ At least 10 suppliers (guaranteed by fallback)
- ✅ Multi-pass search executed
- ✅ 30+ raw candidates harvested
- ✅ Fallback catalog enabled
- ✅ Retry logic configured

---

## [1.0.0] - 2024 - INITIAL RELEASE

### Added
- Complete 8-step agentic workflow
  - Step 1: Machine name normalization
  - Step 2: Query variant generation (3 queries)
  - Step 3: Search execution with diversity
  - Step 4: Company information extraction
  - Step 5: Supplier type classification
  - Step 6: Supplier scoring
  - Step 7: Intelligent expansion
  - Step 8: Deduplication
- Bounded execution (3 queries, 12 pages, 45s timeout)
- Domain diversity control (max 2 results per domain)
- Junk URL filtering (forums, PDFs, marketplaces)
- BeautifulSoup-based company extraction
- Rule-based supplier classification
- Multi-factor scoring algorithm
- Canonical machine name mapping (French → English)
- Industry keyword extraction
- HS code mapping
- Parallel batch processing
- Caching support
- Comprehensive test suite (30 tests)
- Validation script
- Complete documentation
  - `AGENTIC_SOURCING_README.md`
  - `IMPLEMENTATION_SUMMARY.md`
  - `COMPLETE_OVERVIEW.md`

### Configuration
- `max_queries`: 3
- `max_results_per_query`: 10
- `max_pages_total`: 12
- `domain_diversity_cap`: 2
- `target_suppliers_min`: 15
- `target_suppliers_max`: 30
- `candidate_cap`: 30
- `min_confidence_score`: 0.3
- `timeout_per_machine`: 45s
- `use_llm_ranking`: False
- `max_llm_calls`: 1

### Typical Results
- Execution time: ~30-45s
- Suppliers found: 15-30
- Quality: High (OEM + distributors + service)
