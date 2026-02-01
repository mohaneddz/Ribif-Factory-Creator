# Zero-Shot Enrichment - Quick Start Guide

## 🚀 Quick Start

### 1. Basic Usage (Automatic in Module 1)

The zero-shot enrichment is **automatically enabled** in Module 1. Just process your documents as usual:

```python
# In Module 1 route - enrichment happens automatically
POST /api/module1/process
```

The system will:
- Extract machines from your document
- Use AI to generate smart search queries
- Find real machines, specs, and suppliers
- Fill gaps with educated estimates
- Convert everything to DZD

### 2. Standalone Usage

```python
from utils.module_1.zero_shot_enricher import enrich_machine_zero_shot

machine = {
    "nom_machine": "Machine d'injection plastique",
    "description": "Injection plastique (100T → 5000T)",
    "type": "Injection molding machine"
}

enriched = enrich_machine_zero_shot(machine, max_queries=2)
```

## ⚙️ Configuration

Edit [`utils/module_1/zero_shot_config.py`](utils/module_1/zero_shot_config.py):

```python
# Query budget
MAX_QUERIES_PER_MACHINE = 2  # Increase for complex equipment

# Currency
USD_TO_DZD_RATE = 160        # Update based on current rate
IMPORT_TARIFF_RATE = 0.15    # 15% import tariff

# Enable/disable
ENABLE_ZERO_SHOT_ENRICHMENT = True
```

## 📊 Understanding the Output

### Key Fields

```json
{
  "nom_machine": "Machine d'injection plastique",
  "specifications": {
    "manufacturer": "Haitian",
    "capacity": "500 tons",
    "power": "55 kW",
    "dimensions": "6.5m x 3.2m x 2.8m"
  },
  "pricing": {
    "amount_dzd": 46000000,      // Price in DZD
    "includes_tariff": true,      // With 15% import tariff
    "tariff_rate": "15%"
  },
  "suppliers": [
    {"name": "SOMEPI", "location": "Algeria"}
  ],
  "confidence": "high",           // low/medium/high
  "gaps": [],                     // Remaining unfilled fields
  "enrichment_metadata": {
    "queries_used": 2,            // Out of max allowed
    "queries_history": [...],     // What was searched
    "processing_time_s": 15.3,
    "final_confidence": "high"
  }
}
```

### Confidence Levels

- **High:** Multiple sources confirm data, manufacturer identified, minimal estimation
- **Medium:** Single source or some estimated specs with industry standards
- **Low:** Mostly estimations, no specific manufacturer found

## 🎯 How It Works (Simple Explanation)

```
1. EXTRACT
   Document: "Injection plastique (100T → 5000T)"
   ↓

2. ANALYZE GAPS
   AI: "Missing: manufacturer, model, price, suppliers"
   ↓

3. GENERATE QUERIES (Query 1/2)
   AI: "Haitian Arburg injection molding 100-5000 ton Algeria"
   ↓

4. SEARCH WEB
   Found: Manufacturer brands, specs, prices
   ↓

5. ANALYZE AGAIN
   AI: "Still need: dimensions, Algeria suppliers"
   ↓

6. REFINED QUERY (Query 2/2)
   AI: "Haitian 500T dimensions Algeria distributor"
   ↓

7. ESTIMATE REMAINING
   AI: "Weight ≈ 12,000 kg (based on 500T standard)"
   ↓

8. CONVERT TO DZD
   $250,000 × 160 × 1.15 = 46,000,000 DZD
   ↓

9. DONE ✓
```

## 🔧 Common Adjustments

### Increase Query Budget for Complex Equipment

```python
# In zero_shot_config.py
MAX_QUERIES_PER_MACHINE = 4  # Default is 2
```

### Update Currency Rate

```python
# In zero_shot_config.py
USD_TO_DZD_RATE = 165  # Current market rate
```

### Adjust Tariffs

```python
# In zero_shot_config.py
IMPORT_TARIFF_RATE = 0.20  # 20% instead of 15%
```

## 🐛 Troubleshooting

### Issue: Low confidence results

**Solution:** 
- Provide more detailed machine descriptions in input
- Increase `MAX_QUERIES_PER_MACHINE` to 3-4
- Check if web search is enabled (`WEB_SEARCH_ENABLED = True`)

### Issue: No suppliers found

**Solution:**
- AI will estimate based on typical distribution channels
- Algeria has limited online presence - this is expected
- Review `SUPPLIER_REGION_PRIORITY` in config

### Issue: Pricing seems off

**Solution:**
- Check `USD_TO_DZD_RATE` is current
- Review `IMPORT_TARIFF_RATE` for your equipment type
- Estimated prices are conservative - validate with quotes

### Issue: Too slow

**Solution:**
- Reduce `MAX_QUERIES_PER_MACHINE` to 1
- Enable search caching: `ENABLE_SEARCH_CACHE = True`
- Reduce parallel machines: `MAX_PARALLEL_MACHINES = 3`

## 📈 Performance Tips

### Batch Processing
Process multiple machines in parallel (default: 7 concurrent)

### Caching
Search results are cached for 24 hours by default

### Query Optimization
- More specific input = fewer queries needed
- Good: "Haitian 500T injection machine"
- Bad: "plastic machine"

## 🔍 Monitoring

### Check Query Usage
```python
metadata = enriched["enrichment_metadata"]
print(f"Used {metadata['queries_used']} queries")
print(f"Searches: {metadata['queries_history']}")
```

### Check Confidence
```python
if enriched["confidence"] == "low":
    print("Warning: Mostly estimated data")
    print(f"Gaps: {enriched['gaps']}")
```

### Check Processing Time
```python
time = enriched["enrichment_metadata"]["processing_time_s"]
if time > 30:
    print("Warning: Slow enrichment, consider reducing query budget")
```

## 🎓 Examples

### Example 1: Clear Input (Uses 1 query)
```python
Input: "Arburg Allrounder 500T injection molding machine"
Queries: 1 (specific brand known)
Confidence: High
Time: ~8 seconds
```

### Example 2: Vague Input (Uses 2 queries)
```python
Input: "Injection plastique (100T → 5000T)"
Queries: 2 (needs to find brands first)
Confidence: Medium-High
Time: ~15 seconds
```

### Example 3: Rare Equipment (Uses max queries + estimation)
```python
Input: "Ultra-thin glass lamination machine"
Queries: 2 (hits limit)
Confidence: Medium
Time: ~18 seconds
Result: Manufacturers estimated, specs estimated, prices estimated
```

## 📚 Further Reading

- [Full Documentation](ZERO_SHOT_ENRICHMENT_GUIDE.md)
- [Configuration Reference](utils/module_1/zero_shot_config.py)
- [Test Suite](test_zero_shot_enrichment.py)

## 💡 Pro Tips

1. **Better Descriptions = Better Results**
   - Include capacity, brand if known, purpose
   
2. **Trust the Estimates**
   - All estimates have engineering rationale
   - Review rationale in `specifications.{field}_rationale`

3. **Algeria Focus**
   - System prioritizes local suppliers
   - Falls back to MENA → Europe → Asia

4. **Monitor Costs**
   - Each query = 1 LLM call + 1 web search
   - Default 2 queries = ~$0.01-0.02 per machine

5. **Validate Critical Data**
   - Use enriched data as starting point
   - Get actual quotes for final decisions
   - DZD conversions are estimates

## 🚦 Status Indicators

| Indicator | Meaning |
|-----------|---------|
| `confidence: "high"` | Web-verified data, multiple sources |
| `confidence: "medium"` | Mix of web and estimates |
| `confidence: "low"` | Mostly estimates |
| `gaps: []` | All fields filled |
| `gaps: ["price"]` | Some fields missing/estimated |
| `value_source: "web_enriched"` | From web search |
| `value_source: "estimation"` | AI estimation |

---

**Need Help?** Check logs at `logs/run.txt` or review query history in output metadata.
