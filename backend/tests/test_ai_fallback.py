"""
Unit Tests for AI Fallback Supplier Generation

Tests the AI fallback system that generates suppliers when no
public suppliers are found, using domain knowledge and typical manufacturers.
"""

import unittest
from utils.module_4.ai_fallback import (
    generate_ai_fallback_suppliers,
    add_no_suppliers_subtext,
    detect_category_from_canonical,
    CURATED_SUPPLIERS_BY_CATEGORY,
)


class TestCategoryDetection(unittest.TestCase):
    """Test category detection from canonical machine names."""
    
    def test_glass_machinery_detection(self):
        """Test detection of glass machinery categories."""
        test_cases = [
            ("Glass Tempering Furnace", "glass_tempering"),
            ("Glass Lamination Line", "glass_lamination"),
            ("Glass Bending Machine", "glass_bending"),
        ]
        
        for canonical_name, expected_category in test_cases:
            category = detect_category_from_canonical(canonical_name)
            self.assertEqual(category, expected_category, f"Failed for: {canonical_name}")
    
    def test_plastic_machinery_detection(self):
        """Test detection of plastic machinery categories."""
        test_cases = [
            ("Polymer Extrusion Line", "extrusion"),
            ("Thermoforming Machine", "thermoforming"),
            ("Plastic Injection Molding Machine", "injection_molding"),
        ]
        
        for canonical_name, expected_category in test_cases:
            category = detect_category_from_canonical(canonical_name)
            self.assertEqual(category, expected_category, f"Failed for: {canonical_name}")
    
    def test_robotics_detection(self):
        """Test detection of robotics categories."""
        category = detect_category_from_canonical("Industrial Painting Robot")
        self.assertEqual(category, "painting_robot")
    
    def test_generic_fallback(self):
        """Test fallback to generic category for unknown machines."""
        category = detect_category_from_canonical("Some Unknown Machine Type")
        self.assertEqual(category, "generic")


class TestAIFallbackGeneration(unittest.TestCase):
    """Test AI fallback supplier generation."""
    
    def test_generate_with_typical_manufacturers(self):
        """Test generation using typical manufacturers from Phase B."""
        typical_mfrs = ["Glaston", "Bystronic Glass", "Hegla"]
        
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Glass Tempering Furnace",
            typical_manufacturers=typical_mfrs,
            max_suppliers=3
        )
        
        # Should generate suppliers
        self.assertGreater(len(ai_suppliers), 0)
        self.assertLessEqual(len(ai_suppliers), 3)
        
        # All should be marked as AI-generated
        for supplier in ai_suppliers:
            self.assertTrue(supplier.get('is_ai_fallback', False))
            self.assertIn('availability_note', supplier)
            self.assertIn('AI suggestion', supplier['notes'])
    
    def test_generate_without_typical_manufacturers(self):
        """Test generation using curated suppliers only."""
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Thermoforming Machine",
            typical_manufacturers=None,
            max_suppliers=3
        )
        
        # Should generate from curated list
        self.assertGreater(len(ai_suppliers), 0)
        self.assertLessEqual(len(ai_suppliers), 3)
        
        # All should be marked as AI-generated
        for supplier in ai_suppliers:
            self.assertTrue(supplier.get('is_ai_fallback', False))
    
    def test_supplier_structure_completeness(self):
        """Test that generated suppliers have all required fields."""
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Injection Molding Machine",
            max_suppliers=2
        )
        
        required_fields = [
            'supplier_name', 'region', 'website', 'price_estimate',
            'price_type', 'notes', 'relevance_score', 'is_ai_fallback', 'ai_tag',
            'availability_note', 'emails', 'phones', 'contact_pages',
            'quality_score', 'evidence'
        ]
        
        for supplier in ai_suppliers:
            for field in required_fields:
                self.assertIn(field, supplier, f"Missing field: {field}")
    
    def test_deduplication_with_typical_manufacturers(self):
        """Test that typical manufacturers don't duplicate curated suppliers."""
        typical_mfrs = ["ILLIG", "Kiefel"]  # These exist in curated thermoforming list
        
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Thermoforming Machine",
            typical_manufacturers=typical_mfrs,
            max_suppliers=5
        )
        
        # Check no duplicate supplier names
        names = [s['supplier_name'].lower() for s in ai_suppliers]
        self.assertEqual(len(names), len(set(names)), "Found duplicate suppliers")
    
    def test_max_suppliers_limit(self):
        """Test that max_suppliers limit is respected."""
        for max_count in [1, 2, 3, 5]:
            ai_suppliers = generate_ai_fallback_suppliers(
                canonical_name="Extrusion Line",
                max_suppliers=max_count
            )
            
            self.assertLessEqual(len(ai_suppliers), max_count)
    
    def test_curated_suppliers_exist(self):
        """Test that curated supplier maps are properly populated."""
        # Check key categories have suppliers
        important_categories = [
            'glass_tempering', 'extrusion', 'thermoforming',
            'injection_molding', 'painting_robot'
        ]
        
        for category in important_categories:
            self.assertIn(category, CURATED_SUPPLIERS_BY_CATEGORY)
            suppliers = CURATED_SUPPLIERS_BY_CATEGORY[category]
            self.assertGreater(len(suppliers), 0, f"No suppliers for {category}")
            
            # Check supplier structure
            for supplier in suppliers:
                self.assertIn('supplier_name', supplier)
                self.assertTrue(supplier.get('is_ai_fallback'))
                self.assertEqual(supplier.get('ai_tag'), '★')


class TestNoSuppliersSubtext(unittest.TestCase):
    """Test addition of no_public_suppliers_subtext."""
    
    def test_add_subtext_when_all_ai(self):
        """Test subtext is added when all suppliers are AI-generated."""
        machine_result = {
            "machine_input": {"canonical_name": "Test Machine"},
            "suppliers": [
                {"supplier_name": "AI Supplier 1", "ai_star": True},
                {"supplier_name": "AI Supplier 2", "ai_star": True},
            ]
        }
        
        result = add_no_suppliers_subtext(machine_result)
        
        self.assertIn('no_public_suppliers_subtext', result)
        self.assertIn('No public suppliers available', result['no_public_suppliers_subtext'])
    
    def test_add_subtext_when_empty(self):
        """Test subtext is added when suppliers list is empty."""
        machine_result = {
            "machine_input": {"canonical_name": "Test Machine"},
            "suppliers": []
        }
        
        result = add_no_suppliers_subtext(machine_result)
        
        self.assertIn('no_public_suppliers_subtext', result)
    
    def test_no_subtext_when_real_suppliers(self):
        """Test subtext is NOT added when real suppliers exist."""
        machine_result = {
            "machine_input": {"canonical_name": "Test Machine"},
            "suppliers": [
                {"supplier_name": "Real Supplier", "ai_star": False},
                {"supplier_name": "AI Supplier", "ai_star": True},
            ]
        }
        
        result = add_no_suppliers_subtext(machine_result)
        
        self.assertNotIn('no_public_suppliers_subtext', result)
    
    def test_no_subtext_when_mixed_with_non_ai(self):
        """Test subtext is NOT added when at least one non-AI supplier exists."""
        machine_result = {
            "machine_input": {"canonical_name": "Test Machine"},
            "suppliers": [
                {"supplier_name": "Real Supplier"},  # Missing ai_star defaults to False
                {"supplier_name": "AI Supplier", "ai_star": True},
            ]
        }
        
        result = add_no_suppliers_subtext(machine_result)
        
        self.assertNotIn('no_public_suppliers_subtext', result)


class TestIntegrationScenarios(unittest.TestCase):
    """Test realistic integration scenarios."""
    
    def test_scenario_zero_public_suppliers_glass(self):
        """Test generating AI fallback for glass machinery with no public suppliers."""
        typical_mfrs = ["Glaston", "Bystronic Glass"]
        
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Glass Tempering Furnace",
            typical_manufacturers=typical_mfrs,
            max_suppliers=3
        )
        
        # Should generate suppliers combining typical manufacturers and curated
        self.assertGreaterEqual(len(ai_suppliers), 2)
        
        # Check quality
        for supplier in ai_suppliers:
            self.assertTrue(supplier.get('is_ai_fallback'))
            self.assertNotIn('â', supplier['price_estimate'])
    
    def test_scenario_zero_public_suppliers_plastic(self):
        """Test generating AI fallback for plastic machinery."""
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Thermoforming Machine",
            typical_manufacturers=["ILLIG", "Kiefel"],
            max_suppliers=3
        )
        
        self.assertGreaterEqual(len(ai_suppliers), 2)
        
        # Should include known manufacturers
        names = ' '.join(s['supplier_name'] for s in ai_suppliers)
        self.assertTrue('ILLIG' in names or 'Kiefel' in names)
    
    def test_scenario_unknown_machine_type(self):
        """Test fallback for completely unknown machine types."""
        ai_suppliers = generate_ai_fallback_suppliers(
            canonical_name="Futuristic Quantum Machine",
            typical_manufacturers=None,
            max_suppliers=2
        )
        
        # Should still generate generic fallback
        self.assertGreater(len(ai_suppliers), 0)
        
        # Should be marked as generic/AI suggestion
        for supplier in ai_suppliers:
            self.assertTrue(supplier.get('is_ai_fallback'))


if __name__ == "__main__":
    unittest.main()
