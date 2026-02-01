# Hardening Utilities Quick Reference
**Target Audience**: Developers working on RIBIF modules

## When to Use Each Utility

### 1. Normalization (`utils/normalization.py`)

#### Use `normalize_numeric()` when:
- Comparing numeric values from external sources
- Processing user inputs (prices, quantities, dimensions)
- Handling LLM outputs (might return strings or dicts)
- Summing or calculating with mixed types

```python
from utils.normalization import normalize_numeric

# API response might have various formats
price = normalize_numeric(data.get("price"), default=0.0)
qty = normalize_numeric(machine["quantity"], default=1)

# Safe comparison (won't crash if types are wrong)
if normalize_numeric(score) > 0.5:
    ...
```

#### Use `canonicalize_key()` when:
- Matching entity names (suppliers, machines, materials)
- Comparing user inputs to database records
- Deduplicating entities

```python
from utils.normalization import canonicalize_key

# Match despite case/spacing differences
if canonicalize_key("ACME Corp.") == canonicalize_key("acme corp"):
    # Match found!
```

#### Use `safe_sum()` when:
- Totaling prices across multiple suppliers
- Aggregating quantities from various sources
- Summing confidence scores

```python
from utils.normalization import safe_sum

# Handles [100, "50", {"value": 25}, None, 10]
total = safe_sum(prices)  # Returns 185.0
```

---

### 2. Quota Management (`utils/quota_manager.py`)

#### Use `@with_quota_check` when:
- Calling expensive APIs (Vertex AI, Serper, etc.)
- Operations that cost money per call
- Want to prevent runaway costs

```python
from utils.quota_manager import with_quota_check

@with_quota_check("vertex_ai", max_calls=100)
def call_gemini(prompt: str):
    return generate_message(prompt)
```

#### Use `@with_rate_limit` when:
- Calling rate-limited APIs
- Want to prevent 429 errors
- Need exponential backoff

```python
from utils.quota_manager import with_rate_limit

@with_rate_limit("serper_api", min_delay=1.0)
def search_web(query: str):
    return serper.search(query)
```

#### Use `@with_retry` when:
- Operations might fail transiently
- Network calls that can time out
- Want automatic retry with backoff

```python
from utils.quota_manager import with_retry

@with_retry(max_attempts=3, catch_quota_errors=True)
def fetch_supplier_data(url: str):
    response = requests.get(url, timeout=10)
    return response.json()
```

#### Handling quota errors gracefully:
```python
from utils.quota_manager import is_quota_error, get_user_friendly_error

try:
    result = expensive_operation()
except Exception as e:
    if is_quota_error(e):
        error_info = get_user_friendly_error(e)
        return {
            "error": error_info["error"],
            "message": error_info["message"],
            "suggestion": error_info["suggestion"]
        }
    raise
```

---

### 3. Pipeline Metrics (`utils/pipeline_metrics.py`)

#### Use when building module pipelines:

```python
from utils.pipeline_metrics import create_pipeline_metrics

def process_module_N(document):
    # Create metrics tracker
    metrics = create_pipeline_metrics("Module_N")
    
    # === EXTRACTION PHASE ===
    metrics.extraction.source_file = document_path
    metrics.extraction.source_pages = len(pages)
    
    # ... do extraction ...
    
    metrics.extraction.entities_extracted = len(entities)
    metrics.extraction.llm_calls_made = 2
    metrics.complete_extraction()  # Logs extraction metrics
    
    # === ENRICHMENT PHASE ===
    metrics.enrichment.budget_queries_allowed = 5
    
    for entity in entities:
        # ... do enrichment ...
        metrics.enrichment.web_searches_performed += 1
        metrics.enrichment.budget_queries_used += 1
    
    metrics.enrichment.items_found = len(enriched_entities)
    metrics.complete_enrichment()  # Logs enrichment metrics
    
    # === FINALIZATION ===
    metrics.final.total_entities = len(enriched_entities)
    metrics.final.fields_complete = count_complete_fields()
    metrics.final.status = "success"
    metrics.final.status_message = "All entities enriched"
    
    metrics.complete_pipeline()  # Logs final metrics
    
    # Include in response
    return {
        "entities": enriched_entities,
        "metrics": metrics.to_dict()
    }
```

---

### 4. External Clients (`utils/external_clients.py`)

#### Use when accessing external services:

```python
from utils.external_clients import get_service_config

config = get_service_config()

# Build API endpoint
vertex_url = config.build_endpoint_url("vertex_ai", "/v1/models/gemini-pro")

# Get service status
if config.is_service_configured("serper"):
    # Proceed with web search
    pass
```

---

## Common Patterns

### Pattern 1: Robust LLM Call with Metrics
```python
from utils.quota_manager import with_quota_check, with_retry
from utils.pipeline_metrics import create_pipeline_metrics

@with_quota_check("vertex_ai", max_calls=100)
@with_retry(max_attempts=2, catch_quota_errors=True)
def call_llm_with_tracking(prompt: str, metrics):
    result = generate_message(prompt)
    metrics.enrichment.llm_calls_made += 1
    return result
```

### Pattern 2: Safe Numeric Processing
```python
from utils.normalization import normalize_numeric, safe_sum

def calculate_total_cost(items):
    prices = [normalize_numeric(item.get("price")) for item in items]
    quantities = [normalize_numeric(item.get("qty"), default=1) for item in items]
    
    total = safe_sum([p * q for p, q in zip(prices, quantities)])
    return total
```

### Pattern 3: Entity Deduplication
```python
from utils.normalization import canonicalize_key

def deduplicate_suppliers(suppliers):
    seen = set()
    unique = []
    
    for supplier in suppliers:
        key = canonicalize_key(supplier["name"])
        if key not in seen:
            seen.add(key)
            unique.append(supplier)
    
    return unique
```

### Pattern 4: Graceful Degradation
```python
from utils.quota_manager import is_quota_error, get_user_friendly_error

def enrich_with_fallback(entity):
    try:
        # Try web enrichment
        return web_enrich(entity)
    except Exception as e:
        if is_quota_error(e):
            logger.warning("Quota exhausted, using estimation")
            return estimate_values(entity)
        raise
```

### Pattern 5: Rate-Limited Batch Processing
```python
from utils.quota_manager import with_rate_limit

@with_rate_limit("web_api", min_delay=0.5)
def fetch_one(url):
    return requests.get(url).json()

def fetch_batch(urls):
    results = []
    for url in urls:
        # Automatically rate-limited
        result = fetch_one(url)
        results.append(result)
    return results
```

---

## Module Integration Checklist

When adding hardening to a new module:

- [ ] Import normalization utils
- [ ] Replace numeric comparisons with `normalize_numeric()`
- [ ] Add `@with_quota_check` to expensive API calls
- [ ] Add `@with_rate_limit` to web searches
- [ ] Add `@with_retry` to unstable operations
- [ ] Create `PipelineMetrics` instance
- [ ] Track extraction metrics
- [ ] Track enrichment metrics
- [ ] Complete and log all metrics
- [ ] Include metrics in response
- [ ] Handle quota errors gracefully
- [ ] Return partial results on failure

---

## Testing Your Changes

### Test Normalization
```python
from utils.normalization import normalize_numeric

# Should not crash
assert normalize_numeric({"value": 100}) == 100.0
assert normalize_numeric("invalid", default=5) == 5
assert normalize_numeric(None) == 0.0
```

### Test Quota Management
```python
from utils.quota_manager import get_quota_tracker, reset_quota_tracker

# Simulate exhaustion
tracker = get_quota_tracker("test_service", max_calls=1)
tracker.record_call()

# Should fail
try:
    @with_quota_check("test_service", max_calls=1)
    def call():
        pass
    call()
    assert False, "Should have raised"
except RuntimeError as e:
    assert "quota exhausted" in str(e).lower()

# Cleanup
reset_quota_tracker("test_service")
```

### Test Health Endpoint
```bash
# System should be healthy
curl http://localhost:5000/health | jq '.status'
# Output: "healthy"

# Check specific service
curl http://localhost:5000/health | jq '.quotas.vertex_ai'
# Output: {"calls_made": 42, "quota_exhausted": false, ...}
```

---

## Error Response Format

All hardened modules should return consistent error responses:

```json
{
  "error": "quota_exceeded",
  "message": "API quota or rate limit exceeded",
  "suggestion": "Please wait a few minutes and try again",
  "technical_details": "Resource exhausted...",
  "partial_results": {...}
}
```

Error codes:
- `quota_exceeded` - API quota hit
- `authentication_failed` - Auth error
- `timeout` - Request timed out
- `connection_error` - Network issue
- `unknown_error` - Unexpected failure

---

## Performance Considerations

- `normalize_numeric()`: ~5μs per call
- `@with_quota_check`: ~10μs per call
- `@with_rate_limit`: Adds configured delay (0.5-1.0s)
- `PipelineMetrics`: ~1KB memory per instance

**Recommendation**: Use liberally - overhead is negligible compared to API calls.
