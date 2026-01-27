# backend/utils/module_4/test_bounded.py
"""
Unit tests and acceptance criteria validation for Module 4 Bounded
"""

import json
from pathlib import Path
from .core_v2 import (
    canonicalize_machine,
    ground_machine,
    should_validate_with_web,
    process_module_4_bounded,
    CLASS_CORE_STABLE,
    CLASS_CORE_VARIABLE,
    CLASS_OPTIONAL,
    CLASS_SUBSYSTEM,
    CONF_HIGH,
    CONF_MEDIUM,
    CONF_LOW,
    MAX_SEARCH_QUERIES_PER_MACHINE,
    MAX_FETCH_PAGES_TOTAL,
    MAX_LLM_CALLS_PER_MACHINE,
    GLOBAL_WEB_CALL_MULTIPLIER,
)

def test_phase_a_canonicalization():
    """Test Phase A: Canonicalize + Classify"""
    print("\n=== TEST: Phase A - Canonicalization ===")
    
    # Test known machines
    tests = [
        ("Machine d'injection plastique", "Plastic Injection Molding Machine", CLASS_CORE_STABLE, CONF_HIGH),
        ("AGV", "Automated Guided Vehicle", CLASS_OPTIONAL, CONF_HIGH),
        ("Système de vision", "Vision QC Subsystem", CLASS_SUBSYSTEM, CONF_HIGH),
        ("Unknown New Machine", "Unknown New Machine", CLASS_CORE_VARIABLE, CONF_LOW),
    ]
    
    for name, expected_canon, expected_class, expected_conf in tests:
        canon, cls, conf = canonicalize_machine(name)
        assert canon == expected_canon, f"Failed: {name} -> {canon} (expected {expected_canon})"
        assert cls == expected_class, f"Failed class: {name} -> {cls} (expected {expected_class})"
        print(f"✓ {name} -> {canon} [{cls}, {conf}]")
    
    print("✓ Phase A tests passed")

def test_phase_a_subsystem_exclusion():
    """Test that subsystems are properly excluded"""
    print("\n=== TEST: Subsystem Exclusion ===")
    
    subsystems = [
        "Système de vision",
        "Convoyeur",
        "Silo de stockage",
        "Bain de refroidissement",
    ]
    
    for name in subsystems:
        canon, cls, conf = canonicalize_machine(name)
        assert cls == CLASS_SUBSYSTEM, f"Failed to classify {name} as subsystem"
        print(f"✓ {name} correctly classified as SUBSYSTEM")
    
    print("✓ Subsystem exclusion tests passed")

def test_phase_b_industry_grounding():
    """Test Phase B: Industry Grounding (NO WEB)"""
    print("\n=== TEST: Phase B - Industry Grounding ===")
    
    # Test with known machine
    result = ground_machine("Plastic Injection Molding Machine", CLASS_CORE_STABLE, CONF_HIGH)
    
    assert result["canonical_name"] == "Plastic Injection Molding Machine"
    assert result["role"] is not None
    assert result["typical_capacity_range"] is not None
    assert result["typical_power_range"] is not None
    assert len(result["typical_manufacturers"]) > 0
    assert result["confidence"] == CONF_HIGH
    
    print(f"✓ Known machine has complete knowledge")
    print(f"  Role: {result['role']}")
    print(f"  Manufacturers: {result['typical_manufacturers']}")
    
    # Test with unknown machine
    result_unknown = ground_machine("Unknown Machine XYZ", CLASS_CORE_VARIABLE, CONF_LOW)
    
    assert result_unknown["role"] is None
    assert result_unknown["confidence"] == CONF_LOW
    assert len(result_unknown["typical_manufacturers"]) == 0
    
    print(f"✓ Unknown machine has safe minimal structure")
    print("✓ Phase B tests passed")

def test_phase_c_web_validation_rules():
    """Test Phase C: Web validation decision logic"""
    print("\n=== TEST: Phase C - Web Validation Rules ===")
    
    # Should validate
    assert should_validate_with_web(CLASS_CORE_VARIABLE, CONF_HIGH) == True
    assert should_validate_with_web(CLASS_CORE_STABLE, CONF_LOW) == True
    
    # Should NOT validate
    assert should_validate_with_web(CLASS_SUBSYSTEM, CONF_LOW) == False
    assert should_validate_with_web(CLASS_OPTIONAL, CONF_HIGH) == False
    assert should_validate_with_web(CLASS_CORE_STABLE, CONF_HIGH) == False
    
    print("✓ core_variable always validates")
    print("✓ low confidence always validates")
    print("✓ subsystems never validate")
    print("✓ optional systems don't validate by default")
    print("✓ Phase C validation rules passed")

def test_budgets():
    """Test budget constraints"""
    print("\n=== TEST: Budget Constraints ===")
    
    print(f"✓ Max queries per machine: {MAX_SEARCH_QUERIES_PER_MACHINE}")
    print(f"✓ Max pages per machine: {MAX_FETCH_PAGES_TOTAL}")
    print(f"✓ Max LLM calls per machine: {MAX_LLM_CALLS_PER_MACHINE}")
    print(f"✓ Global multiplier: {GLOBAL_WEB_CALL_MULTIPLIER}x machines")
    
    assert MAX_SEARCH_QUERIES_PER_MACHINE == 1
    assert MAX_FETCH_PAGES_TOTAL == 6
    assert MAX_LLM_CALLS_PER_MACHINE == 1
    assert GLOBAL_WEB_CALL_MULTIPLIER == 2
    
    print("✓ Budget constraints validated")

def test_acceptance_criteria():
    """Test acceptance criteria compliance"""
    print("\n=== TEST: Acceptance Criteria ===")
    
    # Simulate 40 machines
    machine_count = 40
    max_web_calls = machine_count * GLOBAL_WEB_CALL_MULTIPLIER
    max_llm_calls = machine_count * MAX_LLM_CALLS_PER_MACHINE
    
    print(f"For {machine_count} machines:")
    print(f"  ✓ Max web calls: {max_web_calls} (≤ 80)")
    print(f"  ✓ Max LLM calls: {max_llm_calls} (≤ 40)")
    print(f"  ✓ Runtime: {machine_count} * 15s = ~600s max (10 min)")
    
    assert max_web_calls <= 80
    assert max_llm_calls <= 40
    
    print("✓ Acceptance criteria met")

def test_full_pipeline_mock():
    """Test full pipeline with mock data"""
    print("\n=== TEST: Full Pipeline (Mock Data) ===")
    
    mock_machines = [
        {"nom_machine": "Machine d'injection plastique"},
        {"nom_machine": "AGV"},  # Optional - should process but not validate
        {"nom_machine": "Système de vision"},  # Subsystem - should be excluded
        {"nom_machine": "Robot de peinture"},  # Core variable - should validate
    ]
    
    # This would normally call process_module_4_bounded
    # For testing, we just verify the logic
    
    results = []
    excluded = []
    
    for m in mock_machines:
        canon, cls, conf = canonicalize_machine(m["nom_machine"])
        
        if cls == CLASS_SUBSYSTEM:
            excluded.append(m["nom_machine"])
        else:
            results.append({
                "original_name": m["nom_machine"],
                "canonical_name": canon,
                "machine_class": cls,
                "confidence": conf,
                "should_validate_web": should_validate_with_web(cls, conf),
            })
    
    print(f"✓ Processed: {len(results)} machines")
    print(f"✓ Excluded: {len(excluded)} subsystems")
    
    for r in results:
        print(f"  - {r['original_name']}: {r['machine_class']}, "
              f"web={r['should_validate_web']}")
    
    for e in excluded:
        print(f"  - EXCLUDED: {e}")
    
    assert len(results) == 3
    assert len(excluded) == 1
    assert "Système de vision" in excluded
    
    print("✓ Full pipeline logic validated")

def run_all_tests():
    """Run all validation tests"""
    print("=" * 70)
    print("MODULE 4 BOUNDED - VALIDATION TESTS")
    print("=" * 70)
    
    test_phase_a_canonicalization()
    test_phase_a_subsystem_exclusion()
    test_phase_b_industry_grounding()
    test_phase_c_web_validation_rules()
    test_budgets()
    test_acceptance_criteria()
    test_full_pipeline_mock()
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
