"""
Quick validation script for Stage 5 refactoring.
Tests the core functions without pytest dependency.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.module_1.stage5_utils import (
    parse_parameter_value,
    normalize_parametres_process,
    generate_step_signature,
    deduplicate_steps_within_group,
    create_hierarchical_stage5_structure
)


def test_parameter_parsing():
    """Test parameter parsing."""
    print("Testing parameter parsing...")
    
    # Test temperature
    value, unit, source, conf = parse_parameter_value("180°C")
    assert value == 180.0 and unit == "°C", "Temperature parsing failed"
    
    # Test pressure
    value, unit, source, conf = parse_parameter_value("5 bar")
    assert value == 5.0 and unit == "bar", "Pressure parsing failed"
    
    # Test cycle time
    value, unit, source, conf = parse_parameter_value("45s")
    assert value == 45.0 and unit == "s", "Cycle time parsing failed"
    
    # Test N/A
    value, unit, source, conf = parse_parameter_value("N/A")
    assert value is None and unit is None, "N/A parsing failed"
    
    # Test dict format
    dict_val = {"valeur": 25, "unite": "°C", "value_source": "estimated", "confidence": "high"}
    value, unit, source, conf = parse_parameter_value(dict_val)
    assert value == 25.0 and unit == "°C", "Dict parsing failed"
    
    print("✓ Parameter parsing tests passed")


def test_normalization():
    """Test parameter normalization."""
    print("\nTesting parameter normalization...")
    
    raw_params = {
        "temperature": "180°C",
        "pression": "5 bar",
        "temps_cycle": "45s"
    }
    
    normalized = normalize_parametres_process(raw_params)
    
    assert "temperature" in normalized, "Missing temperature"
    assert normalized["temperature"]["value"] == 180.0, "Wrong temperature value"
    assert normalized["temperature"]["unit"] == "°C", "Wrong temperature unit"
    
    assert "pressure" in normalized, "Missing pressure"
    assert normalized["pressure"]["value"] == 5.0, "Wrong pressure value"
    
    assert "cycle_time" in normalized, "Missing cycle_time"
    assert normalized["cycle_time"]["value"] == 45.0, "Wrong cycle_time value"
    
    print("✓ Normalization tests passed")


def test_deduplication():
    """Test deduplication."""
    print("\nTesting deduplication...")
    
    steps = [
        {
            "nom_etape": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0},
                "pressure": {"value": 5.0}
            }
        },
        {
            "nom_etape": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0},
                "pressure": {"value": 5.0}
            }
        },
        {
            "nom_etape": "Cooling",
            "parametres_process": {
                "temperature": {"value": 25.0}
            }
        }
    ]
    
    deduped, count = deduplicate_steps_within_group(steps, "Product A")
    
    assert len(deduped) == 2, f"Expected 2 steps, got {len(deduped)}"
    assert count == 1, f"Expected 1 duplicate, got {count}"
    
    print(f"✓ Deduplication tests passed (removed {count} duplicate)")


def test_hierarchical_structure():
    """Test hierarchical structure creation."""
    print("\nTesting hierarchical structure creation...")
    
    raw_processes = [
        {
            "produit": "SPC flooring",
            "etapes": [
                {
                    "step": 1,
                    "name": "Extrusion",
                    "machine": "Extruder",
                    "parametres_process": {
                        "temperature": "180°C",
                        "pression": "5 bar",
                        "temps_cycle": "45s"
                    }
                },
                {
                    "step": 2,
                    "name": "Cooling",
                    "machine": "Cooler",
                    "parametres_process": {
                        "temperature": "25°C",
                        "temps_cycle": "30s"
                    }
                }
            ]
        },
        {
            "produit": "Injection parts",
            "etapes": [
                {
                    "step": 1,
                    "name": "Injection",
                    "machine": "Injection Press",
                    "parametres_process": {
                        "temperature": "200°C",
                        "pression": "150 bar",
                        "temps_cycle": "20s"
                    }
                }
            ]
        }
    ]
    
    result = create_hierarchical_stage5_structure(raw_processes)
    
    # Check structure
    assert "processes" in result, "Missing 'processes'"
    assert "ui_steps" in result, "Missing 'ui_steps'"
    assert "total_steps" in result, "Missing 'total_steps'"
    assert "total_ui_steps" in result, "Missing 'total_ui_steps'"
    assert "total_groups" in result, "Missing 'total_groups'"
    
    # Check counts
    assert result["total_groups"] == 2, f"Expected 2 groups, got {result['total_groups']}"
    assert result["total_steps"] == 3, f"Expected 3 steps, got {result['total_steps']}"
    assert result["total_ui_steps"] == 3, f"Expected 3 ui_steps, got {result['total_ui_steps']}"
    
    # Check processes structure
    assert len(result["processes"]) == 2, f"Expected 2 processes, got {len(result['processes'])}"
    assert result["processes"][0]["product_family"] == "SPC flooring"
    assert len(result["processes"][0]["steps"]) == 2
    assert result["processes"][1]["product_family"] == "Injection parts"
    assert len(result["processes"][1]["steps"]) == 1
    
    # Check ui_steps structure
    assert len(result["ui_steps"]) == 3
    
    # Check numbering
    ui_step1 = result["ui_steps"][0]
    assert ui_step1["group_id"] == "group_1"
    assert ui_step1["local_step_no"] == 1
    assert ui_step1["global_step_no"] == 1
    assert "[SPC flooring]" in ui_step1["nom_etape"]
    
    ui_step2 = result["ui_steps"][1]
    assert ui_step2["group_id"] == "group_1"
    assert ui_step2["local_step_no"] == 2
    assert ui_step2["global_step_no"] == 2
    
    ui_step3 = result["ui_steps"][2]
    assert ui_step3["group_id"] == "group_2"
    assert ui_step3["local_step_no"] == 1  # Resets for new group
    assert ui_step3["global_step_no"] == 3
    
    # Check parameter normalization
    temp = result["processes"][0]["steps"][0]["parametres_process"]["temperature"]
    assert temp["value"] == 180.0, f"Expected 180.0, got {temp['value']}"
    assert temp["unit"] == "°C", f"Expected °C, got {temp['unit']}"
    
    print("✓ Hierarchical structure tests passed")
    print(f"  - Groups: {result['total_groups']}")
    print(f"  - Total steps: {result['total_steps']}")
    print(f"  - UI steps: {result['total_ui_steps']}")


def test_with_real_data():
    """Test with real complete_pipeline.json if available."""
    print("\nTesting with real data...")
    
    data_dir = Path(__file__).parent / "data" / "module_1"
    
    if not data_dir.exists():
        print("⚠ Data directory not found, skipping real data test")
        return
    
    json_files = list(data_dir.glob("*_complete_pipeline.json"))
    
    if not json_files:
        print("⚠ No complete_pipeline.json files found, skipping real data test")
        return
    
    # Use the most recent one
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    
    print(f"  Loading: {latest_file.name}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stage5 = data.get("stage_5_processus_production", {})
    procs = stage5.get("processus_production", [])
    
    if not procs:
        print("⚠ Stage 5 has no processes, skipping")
        return
    
    # Process it
    result = create_hierarchical_stage5_structure(procs)
    
    # Basic assertions
    assert result["total_groups"] > 0, "No groups found"
    assert result["total_steps"] > 0, "No steps found"
    assert result["total_ui_steps"] == result["total_steps"], "UI steps count mismatch"
    assert len(result["processes"]) == result["total_groups"], "Process count mismatch"
    
    # Check ui_steps numbering
    for i, ui_step in enumerate(result["ui_steps"]):
        assert ui_step["global_step_no"] == i + 1, f"Global step numbering broken at index {i}"
    
    # Check local numbering resets per group
    for process in result["processes"]:
        group_id = process["group_id"]
        group_ui_steps = [s for s in result["ui_steps"] if s["group_id"] == group_id]
        
        for i, step in enumerate(group_ui_steps):
            expected_local = i + 1
            assert step["local_step_no"] == expected_local, \
                f"Local step numbering broken in {group_id}: expected {expected_local}, got {step['local_step_no']}"
    
    print(f"✓ Real data test passed")
    print(f"  - Groups: {result['total_groups']}")
    print(f"  - Total steps: {result['total_steps']}")
    print(f"  - Duplicates removed: {result['duplicate_count']}")
    
    # Show group breakdown
    for process in result["processes"]:
        print(f"  - {process['product_family']}: {len(process['steps'])} steps")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 5 Refactoring Validation Tests")
    print("=" * 60)
    
    try:
        test_parameter_parsing()
        test_normalization()
        test_deduplication()
        test_hierarchical_structure()
        test_with_real_data()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
