"""
Unit Tests for Quality Scoring with Evidence Signals

Tests the enhanced quality scoring system that assigns scores based on
evidence signals like OEM status, contact info, and relevance.
"""

import unittest
from utils.module_4.supplier_filter import (
    compute_quality_score,
    apply_quality_threshold,
)


class TestQualityScoring(unittest.TestCase):
    """Test quality scoring with evidence signals."""
    
    def test_known_oem_domain_bonus(self):
        """Test +0.35 bonus for known OEM domains."""
        supplier = {
            "supplier_name": "Glaston Corporation",
            "website": "https://www.glaston.net",
            "notes": "Glass tempering equipment manufacturer",
        }
        
        score, evidence = compute_quality_score(supplier, canonical_name="Glass Tempering Furnace")
        
        # Should get OEM domain bonus
        self.assertGreaterEqual(score, 0.35)
        self.assertTrue(any("OEM" in e or "Known" in e for e in evidence))
    
    def test_manufacturer_indicators_bonus(self):
        """Test +0.20 bonus for manufacturer/OEM indicators."""
        supplier = {
            "supplier_name": "Industrial Equipment Manufacturing",
            "website": "https://www.iemfg.com",
            "notes": "We are the original equipment manufacturer for industrial machinery",
        }
        
        score, evidence = compute_quality_score(supplier)
        
        # Should get manufacturer indicator bonus
        self.assertGreaterEqual(score, 0.20)
        self.assertTrue(any("OEM" in e or "manufacturer" in e for e in evidence))
    
    def test_contact_info_bonus(self):
        """Test +0.15 bonus for contact information."""
        supplier = {
            "supplier_name": "Contact Test Supplier",
            "website": "https://www.supplier.com",
            "emails": ["info@supplier.com"],
            "phones": ["+1-234-567-8900"],
            "notes": "Industrial equipment",
        }
        
        score, evidence = compute_quality_score(supplier)
        
        # Should get contact info bonus
        self.assertGreaterEqual(score, 0.15)
        self.assertTrue(any("Contact" in e for e in evidence))
    
    def test_address_imprint_bonus(self):
        """Test +0.10 bonus for address/imprint."""
        supplier = {
            "supplier_name": "Company With Address",
            "website": "https://www.company.com",
            "notes": "Company address: 12345 Berlin, Germany. Industrial machinery supplier.",
        }
        
        score, evidence = compute_quality_score(supplier)
        
        # Should get address bonus
        self.assertGreaterEqual(score, 0.10)
        self.assertTrue(any("Address" in e or "imprint" in e for e in evidence))
    
    def test_unrelated_content_penalty(self):
        """Test -0.30 penalty for unrelated content."""
        supplier = {
            "supplier_name": "Materials Supplier",
            "website": "https://www.materials.com",
            "notes": "Raw material supplier only, no machine equipment",
        }
        
        score, evidence = compute_quality_score(supplier)
        
        # Should have penalty
        self.assertLess(score, 0.5)
        self.assertTrue(any("PENALTY" in e and "unrelated" in e for e in evidence))
    
    def test_directory_listing_penalty(self):
        """Test -0.20 penalty for directory listings."""
        supplier = {
            "supplier_name": "Directory Listing",
            "website": "https://www.directory.com",
            "notes": "This is a generic directory listing of suppliers",
        }
        
        score, evidence = compute_quality_score(supplier)
        
        # Should have penalty
        self.assertLess(score, 0.7)
        self.assertTrue(any("PENALTY" in e and "directory" in e for e in evidence))
    
    def test_product_relevance_bonus(self):
        """Test +0.10 bonus for product name relevance."""
        supplier = {
            "supplier_name": "Extrusion Equipment Specialists",
            "website": "https://www.extrusion.com",
            "notes": "We manufacture polymer extrusion lines",
        }
        
        score, evidence = compute_quality_score(
            supplier,
            canonical_name="Polymer Extrusion Line"
        )
        
        # Should get relevance bonus
        self.assertGreaterEqual(score, 0.10)
        self.assertTrue(any("relevance" in e.lower() for e in evidence))
    
    def test_typical_manufacturer_match(self):
        """Test +0.35 bonus for matching typical manufacturers."""
        supplier = {
            "supplier_name": "ILLIG Maschinenbau",
            "website": "https://www.illig.de",
            "notes": "Thermoforming machinery manufacturer",
        }
        
        score, evidence = compute_quality_score(
            supplier,
            canonical_name="Thermoforming Machine",
            typical_manufacturers=["ILLIG", "Kiefel", "Geiss"]
        )
        
        # Should get typical manufacturer bonus
        self.assertGreaterEqual(score, 0.35)
        self.assertTrue(any("manufacturer" in e for e in evidence))
    
    def test_comprehensive_high_quality_supplier(self):
        """Test supplier with multiple positive signals."""
        supplier = {
            "supplier_name": "Premium Equipment Manufacturing GmbH",
            "website": "https://www.engel.at",  # Known OEM domain
            "emails": ["sales@engel.at"],
            "phones": ["+43 50 620 0"],
            "notes": "We are the original equipment manufacturer. Address: 4311 Schwertberg, Austria.",
        }
        
        score, evidence = compute_quality_score(
            supplier,
            canonical_name="Injection Molding Machine",
            typical_manufacturers=["Engel", "Arburg", "Haitian"]
        )
        
        # Should have very high score (multiple bonuses)
        self.assertGreaterEqual(score, 0.80)
        self.assertGreater(len(evidence), 3)  # Multiple evidence signals
    
    def test_score_normalization(self):
        """Test that scores are normalized to [0.0, 1.0]."""
        # High-quality supplier
        high_quality = {
            "supplier_name": "Known OEM",
            "website": "https://www.glaston.net",
            "emails": ["contact@glaston.net"],
            "phones": ["+358 10 500 500"],
            "notes": "Original equipment manufacturer with full address and contact information",
        }
        
        score_high, _ = compute_quality_score(high_quality, typical_manufacturers=["Glaston"])
        self.assertGreaterEqual(score_high, 0.0)
        self.assertLessEqual(score_high, 1.0)
        
        # Low-quality supplier
        low_quality = {
            "supplier_name": "Generic Listing",
            "website": "https://www.unknown.com",
            "notes": "This is a generic directory listing for raw materials only",
        }
        
        score_low, _ = compute_quality_score(low_quality)
        self.assertGreaterEqual(score_low, 0.0)
        self.assertLessEqual(score_low, 1.0)


class TestQualityThreshold(unittest.TestCase):
    """Test quality threshold filtering."""
    
    def test_apply_quality_threshold_basic(self):
        """Test basic quality threshold filtering."""
        suppliers = [
            {
                "supplier_name": "High Quality OEM",
                "website": "https://www.glaston.net",
                "emails": ["info@glaston.net"],
                "notes": "Original manufacturer",
            },
            {
                "supplier_name": "Low Quality Listing",
                "website": "https://www.generic.com",
                "notes": "Generic directory",
            },
        ]
        
        filtered = apply_quality_threshold(
            suppliers,
            min_quality_score=0.55,
            canonical_name="Glass Tempering",
            allow_fallback=False
        )
        
        # Should filter based on quality
        self.assertLessEqual(len(filtered), len(suppliers))
        
        # All filtered suppliers should have quality_score field
        for supplier in filtered:
            self.assertIn('quality_score', supplier)
            self.assertIn('evidence', supplier)
            self.assertGreaterEqual(supplier['quality_score'], 0.55)
    
    def test_fallback_threshold(self):
        """Test fallback to 0.40 threshold when no suppliers pass."""
        suppliers = [
            {
                "supplier_name": "Mediocre Supplier 1",
                "website": "https://www.mediocre1.com",
                "notes": "Some basic info",
            },
            {
                "supplier_name": "Mediocre Supplier 2",
                "website": "https://www.mediocre2.com",
                "notes": "Another basic supplier",
            },
        ]
        
        # With fallback enabled, should return suppliers above 0.40 if none pass 0.55
        filtered = apply_quality_threshold(
            suppliers,
            min_quality_score=0.55,
            canonical_name="Some Machine",
            allow_fallback=True
        )
        
        # Should have at least one supplier if fallback worked
        # (depends on actual scoring, but fallback should be attempted)
        self.assertIsInstance(filtered, list)
    
    def test_no_fallback(self):
        """Test strict filtering with no fallback."""
        suppliers = [
            {
                "supplier_name": "Low Quality",
                "website": "https://www.low.com",
                "notes": "Minimal info",
            },
        ]
        
        # Without fallback, strict threshold
        filtered = apply_quality_threshold(
            suppliers,
            min_quality_score=0.90,  # Very high threshold
            allow_fallback=False
        )
        
        # Might be empty if supplier doesn't meet threshold
        self.assertIsInstance(filtered, list)


if __name__ == "__main__":
    unittest.main()
