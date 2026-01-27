"""
Validation Script: Agentic Supplier Sourcing
=============================================

Validates the implementation without requiring external dependencies.
Tests core logic and data structures.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

print("=" * 70)
print("AGENTIC SUPPLIER SOURCING - VALIDATION")
print("=" * 70)

passed = 0
failed = 0

def test(name, condition, message=""):
    global passed, failed
    if condition:
        print(f"[PASS] {name}")
        passed += 1
    else:
        print(f"[FAIL] {name}")
        if message:
            print(f"  {message}")
        failed += 1

print("\n1. Testing imports...")
try:
    from utils.module_4.supplier_sourcing_agentic import (
        normalize_machine_name,
        generate_query_variants,
        is_junk_url,
        extract_domain,
        normalize_company_name,
        deduplicate_suppliers,
        SourcingConfig,
        SupplierCandidate,
        MachineNormalization,
    )
    test("Import core module", True)
except Exception as e:
    test("Import core module", False, str(e))
    sys.exit(1)

print("\n2. Testing machine normalization...")
try:
    result = normalize_machine_name("machine d'injection plastique")
    test("French to English", result.canonical_name == "plastic injection molding machine")
    test("Keywords extracted", len(result.keywords) > 0)
    test("Synonyms generated", len(result.synonyms) > 0)
except Exception as e:
    test("Machine normalization", False, str(e))

print("\n3. Testing query generation...")
try:
    norm = normalize_machine_name("cnc machine")
    config = SourcingConfig()
    queries = generate_query_variants(norm, config)
    test("3 queries generated", len(queries) == 3)
    intents = [q.intent for q in queries]
    test("OEM query present", "oem" in intents)
    test("Distributor query present", "distributor" in intents)
    test("Service query present", "service" in intents)
    test("Regional focus in queries", any(q.regional_focus for q in queries))
except Exception as e:
    test("Query generation", False, str(e))

print("\n4. Testing junk URL filtering...")
try:
    is_junk, _ = is_junk_url("https://example.com/catalog.pdf")
    test("PDF detected as junk", is_junk)
    
    is_junk, _ = is_junk_url("https://forum.example.com/thread")
    test("Forum detected as junk", is_junk)
    
    is_junk, _ = is_junk_url("https://amazon.com/product/123")
    test("Marketplace detected as junk", is_junk)
    
    is_junk, _ = is_junk_url("https://company.com/products")
    test("Valid URL not flagged", not is_junk)
except Exception as e:
    test("Junk URL filtering", False, str(e))

print("\n5. Testing domain extraction...")
try:
    domain = extract_domain("https://www.example.com/page")
    test("www removed", "www." not in domain)
    test("Domain extracted", "example.com" in domain)
except Exception as e:
    test("Domain extraction", False, str(e))

print("\n6. Testing company name normalization...")
try:
    name1 = normalize_company_name("ABC Company Inc.")
    name2 = normalize_company_name("ABC Company")
    test("Suffix removed", name1 == name2)
    
    name3 = normalize_company_name("ACME Industries")
    name4 = normalize_company_name("acme industries")
    test("Case insensitive", name3 == name4)
except Exception as e:
    test("Company name normalization", False, str(e))

print("\n7. Testing deduplication...")
try:
    candidates = [
        SupplierCandidate(
            name="ACME Inc.",
            domain="acme.com",
            url="https://acme.com",
            supplier_type="OEM",
            confidence=0.8,
            score=0.7,
        ),
        SupplierCandidate(
            name="ACME Incorporated",
            domain="acme.com",
            url="https://acme.com/about",
            supplier_type="OEM",
            confidence=0.9,
            score=0.8,
        ),
    ]
    
    deduplicated = deduplicate_suppliers(candidates)
    test("Duplicates removed", len(deduplicated) == 1)
    test("Higher score kept", deduplicated[0].score == 0.8)
except Exception as e:
    test("Deduplication", False, str(e))

print("\n8. Testing configuration...")
try:
    config = SourcingConfig()
    test("Default max_queries", config.max_queries == 3)
    test("Default max_pages", config.max_pages_total == 12)
    test("Default timeout", config.timeout_per_machine == 45.0)
    test("Default target_min", config.target_suppliers_min == 15)
    test("Default target_max", config.target_suppliers_max == 30)
    
    custom_config = SourcingConfig(max_queries=2, max_pages_total=8)
    test("Custom config applied", custom_config.max_queries == 2 and custom_config.max_pages_total == 8)
except Exception as e:
    test("Configuration", False, str(e))

print("\n9. Testing data structures...")
try:
    supplier = SupplierCandidate(
        name="Test Supplier",
        domain="test.com",
        url="https://test.com",
        supplier_type="OEM",
        confidence=0.85,
        score=0.75,
    )
    
    data = supplier.to_dict()
    test("Supplier serialization", isinstance(data, dict))
    test("Supplier fields present", all(k in data for k in ['name', 'domain', 'supplier_type']))
except Exception as e:
    test("Data structures", False, str(e))

print("\n10. Testing integration module...")
try:
    from utils.module_4.agentic_integration import (
        get_sourcing_config_from_env,
        extract_machines_from_module4_input,
        convert_sourcing_result_to_module4_format,
    )
    test("Import integration module", True)
    
    # Test machine extraction
    test_input = {
        "stage_4_machines_equipements": {
            "machines_production": [
                {"nom_machine": "Machine 1"},
                {"nom_machine": "Machine 2"},
            ]
        }
    }
    
    machines = extract_machines_from_module4_input(test_input)
    test("Machine extraction", len(machines) == 2)
    test("Machine names extracted", machines[0] == "Machine 1")
except Exception as e:
    test("Integration module", False, str(e))

print("\n" + "=" * 70)
print(f"VALIDATION COMPLETE: {passed} passed, {failed} failed")
print("=" * 70)

if failed == 0:
    print("\n✓ All validations passed!")
    print("\nImplementation is ready for use.")
    print("\nNext steps:")
    print("  1. Review documentation: AGENTIC_SOURCING_README.md")
    print("  2. Run example: python example_agentic_sourcing.py")
    print("  3. Integrate into Module 4 route")
else:
    print(f"\n⚠️  {failed} validation(s) failed")
    print("Please review the errors above.")
    sys.exit(1)
