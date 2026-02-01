# Module 4 Upgrade - Quick Start Guide

## Installation

### 1. Install New Dependencies
```bash
cd backend
pip install phonenumbers
```

All other dependencies (`beautifulsoup4`) are already installed.

---

## Verify Installation

### Quick Test Script
Create `test_installation.py`:

```python
# Test imports
try:
    from utils.module_4.contact_extractor import extract_contacts_from_html
    print("✓ contact_extractor imported")
except Exception as e:
    print(f"✗ contact_extractor failed: {e}")

try:
    from utils.module_4.ai_fallback import generate_ai_fallback_suppliers
    print("✓ ai_fallback imported")
except Exception as e:
    print(f"✗ ai_fallback failed: {e}")

try:
    from utils.module_4.supplier_filter import compute_quality_score
    print("✓ supplier_filter enhanced functions imported")
except Exception as e:
    print(f"✗ supplier_filter failed: {e}")

try:
    from routes.module_5 import transform_module4_suppliers
    print("✓ module_5 compatibility layer imported")
except Exception as e:
    print(f"✗ module_5 failed: {e}")

try:
    from supabase_utils import validate_module4_output
    print("✓ supabase_utils validation imported")
except Exception as e:
    print(f"✗ supabase_utils failed: {e}")

print("\n✅ All modules imported successfully!")
```

Run:
```bash
python test_installation.py
```

---

## Run Tests

### Run All Tests
```bash
# Contact extraction tests
python -m unittest tests.test_contact_extraction

# Quality scoring tests
python -m unittest tests.test_quality_scoring

# AI fallback tests
python -m unittest tests.test_ai_fallback

# Module 4→5 handoff tests
python -m unittest tests.test_module4_to_module5_handoff
```

### Expected Results
- All tests should pass
- Total: ~62 tests
- Any failures indicate integration issues

---

## Test Module 4 Enrichment

### Minimal Test
Create `test_module4_enrichment.py`:

```python
from utils.module_4.core_v2 import process_module_4_bounded

# Sample machines
machines = [
    {
        "nom_machine": "Machine d'injection plastique",
        "type": "Production",
        "fabricant_recommande": "",
        "quantite_necessaire": 2,
    }
]

# Run enrichment
result = process_module_4_bounded(machines, max_workers=4)

# Check results
print(f"Machines enriched: {len(result['machines_enriched'])}")

for machine in result['machines_enriched']:
    print(f"\nMachine: {machine['machine_input']['canonical_name']}")
    print(f"Suppliers: {len(machine['suppliers'])}")
    
    for supplier in machine['suppliers'][:3]:  # Show first 3
        print(f"  - {supplier['supplier_name']}")
        print(f"    Emails: {supplier.get('emails', [])}")
        print(f"    Phones: {supplier.get('phones', [])}")
        print(f"    Quality: {supplier.get('quality_score', 'N/A')}")
        print(f"    AI Star: {supplier.get('ai_star', False)}")
```

Run:
```bash
python test_module4_enrichment.py
```

### Expected Output
- Machines should have enriched data
- Suppliers should have `emails`, `phones`, `quality_score`, `evidence`, `ai_star` fields
- If no public suppliers found, should see `ai_star: true` suppliers

---

## Test Module 5 Integration

### Test Supplier Transform
Create `test_module5_transform.py`:

```python
from routes.module_5 import transform_module4_suppliers

# Sample Module 4 suppliers
module4_suppliers = [
    {
        "supplier_name": "Test Supplier",
        "emails": ["contact@test.com", "sales@test.com"],
        "phones": ["+1-234-567-8900"],
        "website": "https://www.test.com",
        "region": "USA",
        "price_estimate": "$100,000",
        "quality_score": 0.85,
        "ai_star": False,
    }
]

# Transform to Module 5 schema
module5_suppliers = transform_module4_suppliers(module4_suppliers)

print(f"Transformed {len(module5_suppliers)} suppliers")

for supplier in module5_suppliers:
    print(f"\nSupplier: {supplier['supplier_name']}")
    print(f"  email_address: {supplier.get('email_address')}")
    print(f"  phone: {supplier.get('phone')}")
    print(f"  emails (original): {supplier.get('emails')}")
    print(f"  phones (original): {supplier.get('phones')}")
    print(f"  quality_score: {supplier.get('quality_score')}")
```

Run:
```bash
python test_module5_transform.py
```

### Expected Output
- Suppliers should have `email_address` field (first email)
- Suppliers should have `phone` field (first phone)
- Original `emails` and `phones` arrays should be preserved

---

## Test Supabase Validation

### Test Validation
Create `test_supabase_validation.py`:

```python
from supabase_utils import validate_module4_output

# Sample data with validation issues
data = {
    "machines_enriched": [
        {
            "machine_input": {"canonical_name": "Test Machine"},
            "suppliers": [
                {
                    "supplier_name": "Test Supplier",
                    "emails": ["test@example.com", None, "test@example.com"],  # Has null and duplicate
                    "phones": ["+1-234-567-8900", None],  # Has null
                    "quality_score": "0.85",  # String instead of float
                    "ai_star": 1,  # Int instead of bool
                }
            ]
        }
    ]
}

# Validate
validated = validate_module4_output(data)

# Check results
supplier = validated['machines_enriched'][0]['suppliers'][0]

print(f"Emails (cleaned): {supplier['emails']}")  # Should be deduplicated, no nulls
print(f"Phones (cleaned): {supplier['phones']}")  # Should have no nulls
print(f"Quality score type: {type(supplier['quality_score'])}")  # Should be float
print(f"AI star type: {type(supplier['ai_star'])}")  # Should be bool
```

Run:
```bash
python test_supabase_validation.py
```

### Expected Output
- Arrays should be cleaned (no nulls, deduplicated)
- Types should be correct (float, bool)

---

## Troubleshooting

### Issue: ImportError for phonenumbers
**Solution**: Install phonenumbers
```bash
pip install phonenumbers
```

### Issue: Contact extraction not working
**Possible causes**:
1. Budget exhausted before contact extraction
2. Supplier pages don't have contact info
3. HTML parsing issues

**Debug**:
```python
from utils.module_4.contact_extractor import extract_contacts_from_html

html = "<html><body>Email: test@example.com, Phone: +1-234-567-8900</body></html>"
result = extract_contacts_from_html(html, "https://example.com")
print(result)
```

### Issue: All suppliers have ai_star: true
**Possible causes**:
1. No public suppliers found (web search returned nothing)
2. All candidates failed quality filter
3. Budget exhausted before search completed

**Check**:
- Review Module 4 logs for "No search results" or "All candidates filtered out"
- Verify `WEB_SEARCH_ENABLED=True` in .env
- Check budget settings (should have ~9 calls/machine)

### Issue: Module 5 has no suppliers to negotiate
**Possible causes**:
1. All suppliers are AI-generated without emails
2. Suppliers filtered out in transform (no email_address)

**Check**:
```python
# Check if suppliers have emails
for supplier in module4_output['machines_enriched'][0]['suppliers']:
    print(f"{supplier['supplier_name']}: emails={supplier.get('emails')}")
```

---

## Next Steps

1. **Deploy to production**: Follow deployment checklist in MODULE4_UPGRADE_SUMMARY.md
2. **Monitor performance**: Check budget usage, quality scores, negotiation success rates
3. **Tune parameters**: Adjust quality thresholds, contact extraction limits
4. **Expand AI fallback**: Add more curated suppliers per category
5. **Frontend updates**: Display contact info and quality scores in UI

---

## Support

For issues or questions:
1. Check MODULE4_UPGRADE_SUMMARY.md for detailed documentation
2. Review test files for usage examples
3. Check backend logs for error messages
4. Contact RIBIF development team

**Version**: 1.0.0  
**Last Updated**: February 1, 2026
