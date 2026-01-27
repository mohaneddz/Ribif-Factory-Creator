"""
Integration Tests for Module 4 → Module 5 Handoff

Tests that Module 4 supplier output correctly transforms to Module 5
negotiation schema, including contact field preservation through Supabase.
"""

import unittest
import json
from unittest.mock import Mock, patch
from routes.module_5 import transform_module4_suppliers
from supabase_utils import validate_module4_output


class TestModule4ToModule5Transform(unittest.TestCase):
    """Test transformation of Module 4 suppliers to Module 5 schema."""
    
    def test_transform_emails_array_to_single(self):
        """Test transformation of emails array to email_address."""
        module4_suppliers = [
            {
                "supplier_name": "Test Supplier",
                "emails": ["contact@supplier.com", "sales@supplier.com"],
                "phones": ["+1-234-567-8900"],
                "website": "https://www.supplier.com",
            }
        ]
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        self.assertEqual(len(module5_suppliers), 1)
        supplier = module5_suppliers[0]
        
        # Should have email_address (first email)
        self.assertEqual(supplier['email_address'], "contact@supplier.com")
        
        # Should preserve original emails array
        self.assertEqual(supplier['emails'], ["contact@supplier.com", "sales@supplier.com"])
    
    def test_transform_phones_array_to_single(self):
        """Test transformation of phones array to phone."""
        module4_suppliers = [
            {
                "supplier_name": "Test Supplier",
                "emails": ["info@test.com"],
                "phones": ["+33 1 42 86 82 00", "+33 1 42 86 82 01"],
                "website": "https://www.test.fr",
            }
        ]
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        supplier = module5_suppliers[0]
        
        # Should have phone (first phone)
        self.assertEqual(supplier['phone'], "+33 1 42 86 82 00")
        
        # Should preserve original phones array
        self.assertEqual(len(supplier['phones']), 2)
    
    def test_filter_suppliers_without_email(self):
        """Test that suppliers without email are filtered out."""
        module4_suppliers = [
            {
                "supplier_name": "With Email",
                "emails": ["contact@withemail.com"],
                "phones": [],
            },
            {
                "supplier_name": "Without Email",
                "emails": [],
                "phones": ["+1-234-567-8900"],
            },
        ]
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        # Should only keep supplier with email
        self.assertEqual(len(module5_suppliers), 1)
        self.assertEqual(module5_suppliers[0]['supplier_name'], "With Email")
    
    def test_preserve_all_module4_fields(self):
        """Test that all Module 4 fields are preserved."""
        module4_suppliers = [
            {
                "supplier_name": "Complete Supplier",
                "emails": ["info@supplier.com"],
                "phones": ["+1-234-567-8900"],
                "contact_pages": ["https://www.supplier.com/contact"],
                "website": "https://www.supplier.com",
                "region": "Europe",
                "price_estimate": "€500,000",
                "price_type": "Ex-works",
                "notes": "Premium manufacturer",
                "relevance_score": 0.9,
                "quality_score": 0.85,
                "evidence": ["Known OEM", "Contact info present"],
                "ai_star": False,
            }
        ]
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        supplier = module5_suppliers[0]
        
        # Check all fields preserved
        self.assertEqual(supplier['supplier_name'], "Complete Supplier")
        self.assertEqual(supplier['website'], "https://www.supplier.com")
        self.assertEqual(supplier['region'], "Europe")
        self.assertEqual(supplier['price_estimate'], "€500,000")
        self.assertEqual(supplier['quality_score'], 0.85)
        self.assertFalse(supplier['ai_star'])
        
        # Check new fields
        self.assertEqual(supplier['email_address'], "info@supplier.com")
        self.assertEqual(supplier['phone'], "+1-234-567-8900")
    
    def test_empty_suppliers_list(self):
        """Test handling of empty suppliers list."""
        module4_suppliers = []
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        self.assertEqual(len(module5_suppliers), 0)
    
    def test_ai_star_suppliers_preserved(self):
        """Test that AI-generated suppliers are properly transformed."""
        module4_suppliers = [
            {
                "supplier_name": "AI Generated Supplier",
                "emails": [],  # AI suppliers might not have emails initially
                "phones": [],
                "ai_star": True,
                "availability_note": "No public suppliers found; AI suggestion",
            }
        ]
        
        module5_suppliers = transform_module4_suppliers(module4_suppliers)
        
        # Should be filtered out (no email)
        self.assertEqual(len(module5_suppliers), 0)


class TestSupabaseValidation(unittest.TestCase):
    """Test Supabase validation of Module 4 output."""
    
    def test_validate_supplier_arrays(self):
        """Test validation sanitizes arrays properly."""
        data = {
            "machines_enriched": [
                {
                    "machine_input": {"canonical_name": "Test Machine"},
                    "suppliers": [
                        {
                            "supplier_name": "Test Supplier",
                            "emails": ["test@example.com", None, "duplicate@test.com", "test@example.com"],
                            "phones": ["+1-234-567-8900", None],
                            "contact_pages": ["https://example.com/contact"],
                            "evidence": ["Evidence 1", "Evidence 2", None],
                        }
                    ]
                }
            ]
        }
        
        validated = validate_module4_output(data)
        
        supplier = validated['machines_enriched'][0]['suppliers'][0]
        
        # Should remove nulls and deduplicate
        self.assertEqual(len(supplier['emails']), 2)  # Deduplicated
        self.assertNotIn(None, supplier['emails'])
        
        self.assertEqual(len(supplier['phones']), 1)  # Null removed
        self.assertNotIn(None, supplier['phones'])
        
        self.assertEqual(len(supplier['evidence']), 2)  # Null removed
    
    def test_validate_string_fields(self):
        """Test validation of string fields."""
        data = {
            "machines_enriched": [
                {
                    "machine_input": {"canonical_name": "Test Machine"},
                    "suppliers": [
                        {
                            "supplier_name": None,
                            "region": "",
                            "website": 123,  # Wrong type
                            "notes": None,
                        }
                    ]
                }
            ]
        }
        
        validated = validate_module4_output(data)
        
        supplier = validated['machines_enriched'][0]['suppliers'][0]
        
        # Should have defaults for None values
        self.assertEqual(supplier['supplier_name'], "Unknown")
        self.assertEqual(supplier['region'], "Unknown")
        self.assertEqual(supplier['website'], "123")  # Converted to string
        self.assertEqual(supplier['notes'], "")
    
    def test_validate_boolean_fields(self):
        """Test validation of boolean fields."""
        data = {
            "machines_enriched": [
                {
                    "machine_input": {"canonical_name": "Test Machine"},
                    "suppliers": [
                        {
                            "supplier_name": "Test",
                            "ai_star": "true",  # String instead of bool
                        },
                        {
                            "supplier_name": "Test2",
                            "ai_star": 1,  # Int instead of bool
                        },
                        {
                            "supplier_name": "Test3",
                            # Missing ai_star
                        }
                    ]
                }
            ]
        }
        
        validated = validate_module4_output(data)
        
        suppliers = validated['machines_enriched'][0]['suppliers']
        
        # All should be converted to boolean
        self.assertTrue(isinstance(suppliers[0]['ai_star'], bool))
        self.assertTrue(isinstance(suppliers[1]['ai_star'], bool))
        self.assertTrue(isinstance(suppliers[2]['ai_star'], bool))
    
    def test_validate_numeric_fields(self):
        """Test validation of numeric scores."""
        data = {
            "machines_enriched": [
                {
                    "machine_input": {"canonical_name": "Test Machine"},
                    "suppliers": [
                        {
                            "supplier_name": "Test",
                            "relevance_score": "0.85",  # String
                            "quality_score": None,
                        }
                    ]
                }
            ]
        }
        
        validated = validate_module4_output(data)
        
        supplier = validated['machines_enriched'][0]['suppliers'][0]
        
        # Should be converted to float
        self.assertEqual(supplier['relevance_score'], 0.85)
        self.assertEqual(supplier['quality_score'], 0.5)  # Default
    
    def test_validate_no_public_suppliers_subtext(self):
        """Test validation of no_public_suppliers_subtext field."""
        data = {
            "machines_enriched": [
                {
                    "machine_input": {"canonical_name": "Test Machine"},
                    "suppliers": [],
                    "no_public_suppliers_subtext": None,
                }
            ]
        }
        
        validated = validate_module4_output(data)
        
        machine = validated['machines_enriched'][0]
        
        # Should be sanitized to empty string
        self.assertEqual(machine['no_public_suppliers_subtext'], "")


class TestEndToEndIntegration(unittest.TestCase):
    """Test complete Module 4 → Validation → Module 5 flow."""
    
    def test_complete_flow(self):
        """Test complete flow from Module 4 output to Module 5 negotiation."""
        # Simulate Module 4 output
        module4_output = {
            "ribif_metadata": {
                "enrichment_method": "Module4",
                "processing_time_seconds": 45.2,
            },
            "machines_enriched": [
                {
                    "machine_input": {
                        "canonical_name": "Injection Molding Machine",
                        "confidence": "high",
                    },
                    "suppliers": [
                        {
                            "supplier_name": "Engel Austria",
                            "emails": ["sales@engel.at", "info@engel.at"],
                            "phones": ["+43 50 620 0"],
                            "contact_pages": ["https://www.engelglobal.com/contact"],
                            "website": "https://www.engelglobal.com",
                            "region": "Austria",
                            "price_estimate": "€200,000 - €500,000",
                            "price_type": "Ex-works",
                            "notes": "Premium injection molding manufacturer",
                            "relevance_score": 0.95,
                            "quality_score": 0.90,
                            "evidence": ["Known OEM domain", "Contact info present"],
                            "ai_star": False,
                        },
                        {
                            "supplier_name": "AI Fallback Supplier",
                            "emails": [],
                            "phones": [],
                            "contact_pages": [],
                            "website": "",
                            "region": "Global",
                            "price_estimate": "Contact for quote",
                            "notes": "AI suggestion",
                            "ai_star": True,
                            "availability_note": "No public suppliers found",
                        }
                    ]
                }
            ]
        }
        
        # Step 1: Validate for Supabase
        validated = validate_module4_output(module4_output)
        
        self.assertIsInstance(validated, dict)
        self.assertIn('machines_enriched', validated)
        
        # Step 2: Extract suppliers for Module 5
        machine = validated['machines_enriched'][0]
        suppliers = machine['suppliers']
        
        # Step 3: Transform for Module 5
        module5_suppliers = transform_module4_suppliers(suppliers)
        
        # Should filter out AI supplier without email
        self.assertEqual(len(module5_suppliers), 1)
        
        # Check Module 5 schema
        supplier = module5_suppliers[0]
        self.assertEqual(supplier['email_address'], "sales@engel.at")
        self.assertEqual(supplier['phone'], "+43 50 620 0")
        
        # Original Module 4 fields should be preserved
        self.assertEqual(len(supplier['emails']), 2)
        self.assertEqual(len(supplier['phones']), 1)
        self.assertEqual(supplier['quality_score'], 0.90)
        self.assertFalse(supplier['ai_star'])
        
        # Can now be used for Module 5 negotiation
        self.assertTrue('email_address' in supplier)
        self.assertTrue(supplier['email_address'])  # Has valid email


if __name__ == "__main__":
    unittest.main()
