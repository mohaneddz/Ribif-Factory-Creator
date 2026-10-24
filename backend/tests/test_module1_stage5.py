"""
Unit tests for Module 1 Stage 5 (Processus de Production) refactored logic.
Tests hierarchy preservation, deduplication, parameter normalization, and UI flattening.
"""

import json
import pytest
from pathlib import Path
from utils.module_1.stage5_utils import (
    parse_parameter_value,
    normalize_parametres_process,
    generate_step_signature,
    deduplicate_steps_within_group,
    create_hierarchical_stage5_structure
)


class TestParameterParsing:
    """Test parameter value parsing from various formats."""
    
    def test_parse_temperature_celsius(self):
        """Test parsing temperature values."""
        value, unit, source, confidence = parse_parameter_value("180°C")
        assert value == 180.0
        assert unit == "°C"
        assert source == "document_extracted"
        assert confidence == "medium"
    
    def test_parse_pressure_bar(self):
        """Test parsing pressure values."""
        value, unit, source, confidence = parse_parameter_value("5 bar")
        assert value == 5.0
        assert unit == "bar"
        assert source == "document_extracted"
        assert confidence == "medium"
    
    def test_parse_cycle_time_seconds(self):
        """Test parsing cycle time in seconds."""
        value, unit, source, confidence = parse_parameter_value("45s")
        assert value == 45.0
        assert unit == "s"
        assert source == "document_extracted"
        assert confidence == "medium"
    
    def test_parse_cycle_time_minutes(self):
        """Test parsing cycle time in minutes."""
        value, unit, source, confidence = parse_parameter_value("15 min")
        assert value == 15.0
        assert unit == "min"
        assert source == "document_extracted"
        assert confidence == "medium"
    
    def test_parse_na_value(self):
        """Test parsing N/A values."""
        value, unit, source, confidence = parse_parameter_value("N/A")
        assert value is None
        assert unit is None
        assert source == "unknown"
        assert confidence == "unknown"
    
    def test_parse_dict_format(self):
        """Test parsing dict format from LLM."""
        dict_value = {
            "valeur": 25,
            "unite": "°C",
            "value_source": "estimated",
            "confidence": "high"
        }
        value, unit, source, confidence = parse_parameter_value(dict_value)
        assert value == 25.0
        assert unit == "°C"
        assert source == "estimated"
        assert confidence == "high"
    
    def test_parse_string_dict(self):
        """Test parsing string representation of dict."""
        str_dict = "{'valeur': 180, 'unite': '°C', 'value_source': 'document_extracted', 'confidence': 'high'}"
        value, unit, source, confidence = parse_parameter_value(str_dict)
        assert value == 180.0
        assert unit == "°C"
        assert source == "document_extracted"
        assert confidence == "high"
    
    def test_parse_continuous_mode(self):
        """Test parsing continuous mode indicators."""
        value, unit, source, confidence = parse_parameter_value("Continu")
        assert value is None
        assert unit is None
        assert source == "estimated"
        assert confidence == "high"


class TestParameterNormalization:
    """Test full parameter normalization."""
    
    def test_normalize_full_parameters(self):
        """Test normalizing complete set of parameters."""
        raw_params = {
            "temperature": "180°C",
            "pression": "5 bar",
            "temps_cycle": "45s",
            "vitesse": "50 m/min"
        }
        
        normalized = normalize_parametres_process(raw_params)
        
        assert "temperature" in normalized
        assert normalized["temperature"]["value"] == 180.0
        assert normalized["temperature"]["unit"] == "°C"
        
        assert "pressure" in normalized
        assert normalized["pressure"]["value"] == 5.0
        assert normalized["pressure"]["unit"] == "bar"
        
        assert "cycle_time" in normalized
        assert normalized["cycle_time"]["value"] == 45.0
        assert normalized["cycle_time"]["unit"] == "s"
    
    def test_normalize_continuous_cycle(self):
        """Test normalizing continuous cycle mode."""
        raw_params = {
            "temperature": "200°C",
            "temps_cycle": "Continu"
        }
        
        normalized = normalize_parametres_process(raw_params)
        
        assert "cycle_mode" in normalized
        assert normalized["cycle_mode"] == "continuous"
        # No numeric cycle in the source, so an estimated default fills it
        assert normalized["cycle_time"]["source"] == "estimated"
    
    def test_normalize_missing_parameters(self):
        """Test normalizing with missing parameters."""
        raw_params = {
            "temperature": "150°C"
        }
        
        normalized = normalize_parametres_process(raw_params)
        
        assert normalized["temperature"]["value"] == 150.0
        # Missing values are estimated rather than left null
        assert normalized["pressure"]["source"] == "estimated"
        assert normalized["cycle_time"]["source"] == "estimated"


class TestStepSignature:
    """Test step signature generation for deduplication."""
    
    def test_signature_generation(self):
        """Test generating signature from step."""
        step = {
            "nom_etape": "Extrusion",
            "name": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0, "unit": "°C"},
                "pressure": {"value": 5.0, "unit": "bar"},
                "cycle_time": {"value": 45.0, "unit": "s"}
            }
        }
        
        sig = generate_step_signature(step, "SPC flooring")
        assert isinstance(sig, str)
        assert len(sig) == 32  # MD5 hash length
    
    def test_signature_consistency(self):
        """Test that identical steps generate same signature."""
        step1 = {
            "nom_etape": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0},
                "pressure": {"value": 5.0},
                "cycle_time": {"value": 45.0}
            }
        }
        
        step2 = {
            "nom_etape": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0},
                "pressure": {"value": 5.0},
                "cycle_time": {"value": 45.0}
            }
        }
        
        sig1 = generate_step_signature(step1, "Product A")
        sig2 = generate_step_signature(step2, "Product A")
        
        assert sig1 == sig2
    
    def test_signature_difference(self):
        """Test that different steps generate different signatures."""
        step1 = {
            "nom_etape": "Extrusion",
            "parametres_process": {
                "temperature": {"value": 180.0}
            }
        }
        
        step2 = {
            "nom_etape": "Injection",
            "parametres_process": {
                "temperature": {"value": 200.0}
            }
        }
        
        sig1 = generate_step_signature(step1, "Product A")
        sig2 = generate_step_signature(step2, "Product A")
        
        assert sig1 != sig2
    
    def test_signature_strips_product_prefix(self):
        """Test that product prefix is removed before signature."""
        step1 = {
            "nom_etape": "[SPC flooring] Extrusion",
            "parametres_process": {}
        }
        
        step2 = {
            "nom_etape": "Extrusion",
            "parametres_process": {}
        }
        
        sig1 = generate_step_signature(step1, "SPC flooring")
        sig2 = generate_step_signature(step2, "SPC flooring")
        
        assert sig1 == sig2


class TestDeduplication:
    """Test step deduplication within groups."""
    
    def test_no_duplicates(self):
        """Test when no duplicates exist."""
        steps = [
            {
                "nom_etape": "Step 1",
                "parametres_process": {"temperature": {"value": 180.0}}
            },
            {
                "nom_etape": "Step 2",
                "parametres_process": {"temperature": {"value": 200.0}}
            }
        ]
        
        deduped, count = deduplicate_steps_within_group(steps, "Product A")
        
        assert len(deduped) == 2
        assert count == 0
    
    def test_with_duplicates(self):
        """Test when duplicates exist."""
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
                "nom_etape": "Injection",
                "parametres_process": {
                    "temperature": {"value": 200.0}
                }
            }
        ]
        
        deduped, count = deduplicate_steps_within_group(steps, "Product A")
        
        assert len(deduped) == 2
        assert count == 1


class TestHierarchicalStructure:
    """Test creating hierarchical Stage 5 structure."""
    
    def test_nested_structure(self):
        """Test processing nested product-based structure."""
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
        assert "processes" in result
        assert "ui_steps" in result
        assert "total_steps" in result
        assert "total_ui_steps" in result
        assert "total_groups" in result
        
        # Check counts
        assert result["total_groups"] == 2
        assert result["total_steps"] == 3
        assert result["total_ui_steps"] == 3
        
        # Check processes structure
        assert len(result["processes"]) == 2
        assert result["processes"][0]["product_family"] == "SPC flooring"
        assert len(result["processes"][0]["steps"]) == 2
        assert result["processes"][1]["product_family"] == "Injection parts"
        assert len(result["processes"][1]["steps"]) == 1
        
        # Check ui_steps structure
        assert len(result["ui_steps"]) == 3
        
        # Check first UI step
        ui_step1 = result["ui_steps"][0]
        assert ui_step1["group_id"] == "group_1"
        assert ui_step1["product_family"] == "SPC flooring"
        assert ui_step1["local_step_no"] == 1
        assert ui_step1["global_step_no"] == 1
        assert "[SPC flooring]" in ui_step1["nom_etape"]
        
        # Check second UI step (still in group 1)
        ui_step2 = result["ui_steps"][1]
        assert ui_step2["group_id"] == "group_1"
        assert ui_step2["local_step_no"] == 2
        assert ui_step2["global_step_no"] == 2
        
        # Check third UI step (group 2)
        ui_step3 = result["ui_steps"][2]
        assert ui_step3["group_id"] == "group_2"
        assert ui_step3["product_family"] == "Injection parts"
        assert ui_step3["local_step_no"] == 1
        assert ui_step3["global_step_no"] == 3
        
        # Check parameter normalization
        assert "temperature" in result["processes"][0]["steps"][0]["parametres_process"]
        temp = result["processes"][0]["steps"][0]["parametres_process"]["temperature"]
        assert temp["value"] == 180.0
        assert temp["unit"] == "°C"
    
    def test_flat_structure(self):
        """Test processing flat structure."""
        raw_processes = [
            {
                "nom_etape": "Step 1",
                "numero_etape": 1,
                "parametres_process": {
                    "temperature": "150°C"
                }
            },
            {
                "nom_etape": "Step 2",
                "numero_etape": 2,
                "parametres_process": {
                    "temperature": "175°C"
                }
            }
        ]
        
        result = create_hierarchical_stage5_structure(raw_processes)
        
        # Check counts
        assert result["total_groups"] == 1
        assert result["total_steps"] == 2
        assert result["total_ui_steps"] == 2
        
        # Check single process group
        assert len(result["processes"]) == 1
        assert result["processes"][0]["product_family"] == "Production"
        assert len(result["processes"][0]["steps"]) == 2
        
        # Check ui_steps
        assert len(result["ui_steps"]) == 2
        assert result["ui_steps"][0]["global_step_no"] == 1
        assert result["ui_steps"][1]["global_step_no"] == 2
    
    def test_empty_structure(self):
        """Test processing empty structure."""
        result = create_hierarchical_stage5_structure([])
        
        assert result["processes"] == []
        assert result["ui_steps"] == []
        assert result["total_steps"] == 0
        assert result["total_ui_steps"] == 0
        assert result["total_groups"] == 0
    
    def test_deduplication_in_structure(self):
        """Test that deduplication happens during structure creation."""
        raw_processes = [
            {
                "produit": "Product A",
                "etapes": [
                    {
                        "step": 1,
                        "name": "Extrusion",
                        "parametres_process": {"temperature": "180°C"}
                    },
                    {
                        "step": 2,
                        "name": "Extrusion",  # Duplicate
                        "parametres_process": {"temperature": "180°C"}
                    },
                    {
                        "step": 3,
                        "name": "Cooling",
                        "parametres_process": {"temperature": "25°C"}
                    }
                ]
            }
        ]
        
        result = create_hierarchical_stage5_structure(raw_processes)
        
        # Should have 2 steps, not 3 (duplicate removed)
        assert result["total_steps"] == 2
        assert result["duplicate_count"] == 1
        assert len(result["processes"][0]["steps"]) == 2
        assert len(result["ui_steps"]) == 2


class TestIntegrationWithRealData:
    """Test with real output data if available."""
    
    def test_with_complete_pipeline_json(self):
        """Test with actual complete_pipeline.json if it exists."""
        data_path = Path(__file__).parent.parent / "data" / "module_1"
        
        # Find the most recent complete_pipeline file
        json_files = list(data_path.glob("*_complete_pipeline.json"))
        
        if not json_files:
            pytest.skip("No complete_pipeline.json files found")
        
        # Use the most recent one
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        stage5 = data.get("stage_5_processus_production", {})
        procs = stage5.get("processus_production", [])
        
        if not procs:
            pytest.skip("Stage 5 has no processes")
        
        # Process it
        result = create_hierarchical_stage5_structure(procs)
        
        # Basic assertions
        assert result["total_groups"] > 0
        assert result["total_steps"] > 0
        assert result["total_ui_steps"] == result["total_steps"]
        assert len(result["processes"]) == result["total_groups"]
        
        # Check ui_steps numbering
        for i, ui_step in enumerate(result["ui_steps"]):
            assert ui_step["global_step_no"] == i + 1
        
        # Check local numbering resets per group
        for process in result["processes"]:
            group_id = process["group_id"]
            group_ui_steps = [s for s in result["ui_steps"] if s["group_id"] == group_id]
            
            for i, step in enumerate(group_ui_steps):
                assert step["local_step_no"] == i + 1
        
        print(f"\n✓ Processed {latest_file.name}:")
        print(f"  - Groups: {result['total_groups']}")
        print(f"  - Total steps: {result['total_steps']}")
        print(f"  - Duplicates removed: {result['duplicate_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
