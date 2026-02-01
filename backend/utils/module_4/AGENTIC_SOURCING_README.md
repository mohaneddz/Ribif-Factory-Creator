# Agentic Supplier Sourcing Workflow for Industrial Machines

## Overview

This implementation provides an **intelligent, bounded, and fast** supplier sourcing workflow optimized for industrial machines in Algeria and North Africa. The system returns **15-30 qualified suppliers per machine** while maintaining strict performance constraints.

## 🎯 Key Features

- **High Volume Results**: 15-30 qualified suppliers per machine (OEM + distributor + integrator + service)
- **Bounded Execution**: Hard limits on queries, pages, and timeouts ensure predictable performance
- **Multi-Step Agentic Workflow**: 8-step intelligent process with adaptive strategies
- **Deduplication**: Smart deduplication by normalized company name + domain
- **Confidence Scoring**: Multi-factor scoring system with evidence tracking
- **Regional Focus**: Optimized for Algeria/North Africa/Maghreb region
- **Best-Effort Filtering**: Automatically relaxes thresholds if strict filtering yields too few results

## 📊 Performance Constraints

| Constraint | Limit | Notes |
|------------|-------|-------|
| Queries per machine | 3 | OEM, distributor, service queries |
| Pages fetched | 12 | Total across all queries |
| LLM calls | 1 (optional) | Only for final ranking if enabled |
| Timeout | 45s | Hard timeout per machine |
| Target suppliers | 15-30 | Configurable, with best-effort fallback |

## 🔄 Workflow Steps

### 1. Machine Name Normalization
- Canonical mapping (French → English)
- Keyword extraction
- Synonym generation
- HS code assignment
- Industry term classification

**Example:**
```python
Input: "Machine d'injection plastique"
Output: {
    canonical_name: "plastic injection molding machine",
    keywords: ["plastic", "injection", "molding", "machine"],
    synonyms: ["IMM", "injection press"],
    hs_code: "8477.10"
}
```

### 2. Query Generation
Generates 3 optimized query variants:
- **Q1 (OEM Focus)**: `{machine} "authorized distributor" "official dealer" {keywords}`
- **Q2 (Distributor)**: `{machine} (distributor OR dealer OR agent) {keywords} (Algeria OR Maghreb)`
- **Q3 (Service)**: `{machine} (maintenance OR service OR "spare parts") {keywords} (Algeria OR Maghreb)`

### 3. Search Execution with Diversity Control
- Executes searches via Serper API
- Enforces domain diversity (max 2 results per domain)
- Filters junk URLs:
  - ❌ PDFs
  - ❌ Forums (Reddit, StackOverflow)
  - ❌ Generic marketplaces (Amazon, eBay)
  - ❌ Social media posts
  - ❌ Personal blogs

### 4. Company Extraction
For each candidate URL:
- Fetches page content (10s timeout)
- Extracts company identity
- Finds contact information (email, phone)
- Detects regional presence
- Identifies relevance signals

### 5. Supplier Classification
Rule-based classification using signals:
- **OEM**: manufacturer mentions, product pages, factory terms
- **Distributor**: distributor/dealer mentions, authorized keywords
- **Integrator**: integration/installation/turnkey terms
- **Service**: maintenance/repair/spare parts mentions

### 6. Scoring & Ranking
Multi-factor scoring (0.0 - 1.0+):

**Positive Factors:**
- ✅ +0.3: Contact info present
- ✅ +0.2: Relevant product terms
- ✅ +0.25: Based in Algeria
- ✅ +0.2: Regional coverage (NA/Maghreb)
- ✅ +0.15: Authorized/dealer wording
- ✅ +0.1: Has contact page
- ✅ +0.05: Has catalog

**Negative Factors:**
- ❌ -0.2: Marketplace listing
- ❌ -0.15: No company identity
- ❌ -0.1: Low classification confidence

### 7. Intelligent Expansion
If < 15 suppliers found and budget remains:
1. Identify OEM suppliers
2. Find their "dealer locator" pages
3. Extract additional distributors
4. Classify and score new candidates

### 8. Deduplication
- Normalize company names (remove Inc, LLC, special chars)
- Deduplicate by (normalized_name, domain) tuple
- Keep entry with highest score

## ⚙️ Configuration

### Environment Variables

```bash
# Query limits
SOURCING_MAX_QUERIES=3              # Max queries per machine
SOURCING_MAX_PAGES=12               # Max pages to fetch

# Supplier targets
SOURCING_TARGET_MIN=15              # Min suppliers target
SOURCING_TARGET_MAX=30              # Max suppliers target

# Quality control
SOURCING_STRICTNESS=balanced        # strict / balanced / relaxed
SOURCING_DOMAIN_CAP=2               # Max results per domain

# Performance
SOURCING_TIMEOUT=45                 # Timeout per machine (seconds)

# Features
SOURCING_ENABLE_CACHE=true          # Enable caching
SOURCING_USE_LLM_RANKING=false      # Enable LLM ranking (optional)
```

### Programmatic Configuration

```python
from utils.module_4.supplier_sourcing_agentic import SourcingConfig

config = SourcingConfig(
    max_queries=3,
    max_pages_total=12,
    target_suppliers_min=15,
    target_suppliers_max=30,
    strictness_level="balanced",
    timeout_per_machine=45.0,
    domain_diversity_cap=2,
    enable_cache=True,
)
```

## 🚀 Usage

### Basic Usage

```python
from utils.module_4.supplier_sourcing_agentic import source_suppliers_for_machine

# Source suppliers for a single machine
result = source_suppliers_for_machine("plastic injection molding machine")

print(f"Found {len(result.suppliers)} suppliers")
print(f"Duration: {result.metrics.duration_seconds:.1f}s")

for supplier in result.suppliers:
    print(f"- {supplier.name} ({supplier.supplier_type}): {supplier.score:.2f}")
```

### Batch Processing

```python
from utils.module_4.supplier_sourcing_agentic import source_suppliers_batch

machines = [
    "plastic injection molding machine",
    "cnc lathe",
    "packaging machine",
]

results = source_suppliers_batch(machines, max_workers=4)

for result in results:
    print(f"{result.machine}: {len(result.suppliers)} suppliers")
```

### Module 4 Integration

```python
from utils.module_4.agentic_integration import process_module4_agentic_sourcing

machines = [
    {"nom_machine": "Machine d'injection plastique"},
    {"nom_machine": "Tour CNC"},
]

output = process_module4_agentic_sourcing(machines, max_workers=4)

# Output is compatible with existing Module 4 structure
print(output["summary"])
```

### Drop-in Replacement for Module 4 Route

```python
# In routes/module4.py
from utils.module_4.agentic_integration import process_module_4_agentic

# Replace existing call:
# result = process_module_4_bounded(machines=machines, max_workers=8)

# With:
result = process_module_4_agentic(machines=machines, max_workers=8)
```

## 📤 Output Format

### Per-Supplier Output

```json
{
  "supplier_name": "ACME Industrial Equipment",
  "supplier_type": "OEM",
  "country": "Algeria",
  "coverage": ["Algeria", "North Africa"],
  "website": "https://acme-industrial.dz",
  "contact_page": "https://acme-industrial.dz/contact",
  "email": "contact@acme-industrial.dz",
  "phone": "+213 21 123 456",
  "confidence": 0.85,
  "score": 0.78,
  "evidence": [
    "Leading manufacturer of industrial machines in Algeria...",
    "Authorized dealer for multiple international brands..."
  ],
  "notes": "Has contact info | Based in Algeria | Authorized mention"
}
```

### Machine-Level Output

```json
{
  "machine_input": {
    "nom_machine": "Machine d'injection plastique",
    "canonical_name": "plastic injection molding machine",
    "keywords": ["plastic", "injection", "molding"]
  },
  "suppliers": [...],
  "enrichment_metadata": {
    "queries_used": [
      "plastic injection molding machine \"authorized distributor\"...",
      "plastic injection molding machine distributor Algeria...",
      "plastic injection molding machine maintenance Algeria..."
    ],
    "suppliers_found": 25,
    "high_confidence": 10,
    "medium_confidence": 12,
    "low_confidence": 3,
    "pages_fetched": 10,
    "duration_seconds": 12.5,
    "warnings": []
  }
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python backend/utils/module_4/test_supplier_sourcing_agentic.py

# Run with pytest
pytest backend/utils/module_4/test_supplier_sourcing_agentic.py -v
```

### Test Coverage

- ✅ Machine name normalization (French → English)
- ✅ Query generation (3 variants with correct intents)
- ✅ Junk URL filtering (PDFs, forums, marketplaces, social media)
- ✅ Domain extraction and diversity control
- ✅ Company name normalization
- ✅ Deduplication logic
- ✅ Supplier classification (OEM, distributor, integrator, service)
- ✅ Scoring system (positive and negative factors)
- ✅ Best-effort behavior (threshold relaxation)
- ✅ Configuration management

## 📊 Performance Metrics

### Per Machine Metrics

```python
result.metrics.to_dict()
# Returns:
{
    "queries_generated": 3,
    "queries_executed": 3,
    "search_results_found": 28,
    "urls_scanned": 28,
    "pages_fetched": 10,
    "pages_failed": 2,
    "candidates_extracted": 22,
    "candidates_filtered": 5,
    "candidates_deduplicated": 3,
    "suppliers_final": 25,
    "suppliers_high_confidence": 10,
    "suppliers_medium_confidence": 12,
    "suppliers_low_confidence": 3,
    "duration_seconds": 12.5,
    "timed_out": false
}
```

## 🎨 Best Practices

### 1. Adjust Configuration Based on Requirements

**For High Quality (fewer but better results):**
```python
config = SourcingConfig(
    strictness_level="strict",
    target_suppliers_min=10,
    target_suppliers_max=15,
    min_confidence_score=0.6,
)
```

**For High Volume (more results, some lower confidence):**
```python
config = SourcingConfig(
    strictness_level="relaxed",
    target_suppliers_min=20,
    target_suppliers_max=40,
    min_confidence_score=0.3,
)
```

### 2. Monitor Metrics

```python
for result in results:
    if result.metrics.timed_out:
        logger.warning(f"Timeout for {result.machine}")
    
    if result.metrics.suppliers_final < 10:
        logger.warning(f"Few suppliers for {result.machine}: {result.warnings}")
```

### 3. Use Parallel Processing

```python
# Process 40 machines with 8 workers
results = source_suppliers_batch(machines, max_workers=8)
# Expected duration: ~60-90 seconds total
```

## 🔍 Troubleshooting

### Few Suppliers Returned

1. Check warnings: `result.warnings`
2. Lower strictness: `strictness_level="relaxed"`
3. Increase pages: `max_pages_total=15`
4. Check if machine name is recognized: `result.normalization.canonical_name`

### Timeout Issues

1. Reduce timeout: `timeout_per_machine=30`
2. Reduce pages: `max_pages_total=8`
3. Reduce workers: `max_workers=2`

### No Contact Information

Contact extraction is best-effort. To improve:
- Supplier websites often have separate contact pages
- Check `supplier.contact_page` for link to contact info
- Manual verification may be needed for some suppliers

## 📁 File Structure

```
backend/utils/module_4/
├── supplier_sourcing_agentic.py     # Core workflow (1300+ lines)
├── agentic_integration.py           # Module 4 integration adapter
├── test_supplier_sourcing_agentic.py # Comprehensive tests
├── AGENTIC_SOURCING_README.md       # This file
└── core_v2.py                       # Existing bounded implementation
```

## 🔄 Integration with Existing Module 4

The agentic workflow can coexist with or replace the existing `core_v2.py` implementation:

**Option 1: Side-by-side** (recommended for testing)
```python
# Use agentic for specific machines
if machine_requires_many_suppliers(machine):
    result = process_module_4_agentic(...)
else:
    result = process_module_4_bounded(...)
```

**Option 2: Full replacement**
```python
# In routes/module4.py, replace import:
from utils.module_4.agentic_integration import process_module_4_agentic as process_module_4_bounded
```

## 🚦 Production Checklist

- [ ] Set environment variables for configuration
- [ ] Test with representative machine samples
- [ ] Monitor metrics and adjust configuration
- [ ] Set up caching if needed (reduces redundant API calls)
- [ ] Configure rate limiting for Serper API
- [ ] Set up logging and monitoring
- [ ] Review and filter results quality
- [ ] Document custom configuration for your use case

## 🤝 Contributing

To extend or modify the workflow:

1. **Add new machine mappings**: Edit `CANONICAL_MACHINE_MAP` in `supplier_sourcing_agentic.py`
2. **Adjust scoring**: Modify `score_supplier()` function
3. **Add classification signals**: Update `classify_supplier_type()` function
4. **Improve extraction**: Enhance `extract_company_info()` function

## 📝 License

Part of the RIBIF Module 4 system.

---

**Questions or Issues?** Check the test file for usage examples or contact the development team.
