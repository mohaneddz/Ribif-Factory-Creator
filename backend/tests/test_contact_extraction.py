"""
Unit Tests for Contact Extraction Module

Tests email extraction, phone extraction, and contact page discovery.
"""

import unittest
from utils.module_4.contact_extractor import (
    extract_emails_from_text,
    extract_phones_from_text,
    discover_contact_pages,
    extract_contacts_from_html,
    detect_region_from_url,
    _is_valid_email,
    _normalize_phone,
)


class TestEmailExtraction(unittest.TestCase):
    """Test email address extraction and validation."""
    
    def test_basic_email_extraction(self):
        """Test extraction of standard email formats."""
        text = "Contact us at info@example.com or sales@company.org"
        emails = extract_emails_from_text(text)
        
        self.assertEqual(len(emails), 2)
        self.assertIn("info@example.com", emails)
        self.assertIn("sales@company.org", emails)
    
    def test_email_normalization(self):
        """Test email normalization (lowercase, deduplication)."""
        text = "Contact Info@Example.COM or INFO@example.com"
        emails = extract_emails_from_text(text)
        
        self.assertEqual(len(emails), 1)  # Deduplicated
        self.assertEqual(emails[0], "info@example.com")  # Lowercase
    
    def test_email_filtering(self):
        """Test filtering of invalid emails."""
        text = """
        Valid: contact@company.com
        Invalid: image.png@placeholder
        Invalid: test@example.com
        Invalid: user@domain
        """
        emails = extract_emails_from_text(text)
        
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0], "contact@company.com")
    
    def test_email_validation(self):
        """Test _is_valid_email helper function."""
        self.assertTrue(_is_valid_email("valid@domain.com"))
        self.assertTrue(_is_valid_email("name.surname@company.co.uk"))
        
        self.assertFalse(_is_valid_email("image.png@host"))
        self.assertFalse(_is_valid_email("test@example.com"))  # Filtered domain
        self.assertFalse(_is_valid_email("short@x"))  # Too short domain
        self.assertFalse(_is_valid_email("no-at-sign.com"))


class TestPhoneExtraction(unittest.TestCase):
    """Test phone number extraction and normalization."""
    
    def test_basic_phone_extraction(self):
        """Test extraction of various phone formats."""
        text = "Call us: +1-234-567-8900 or (123) 456-7890"
        phones = extract_phones_from_text(text, default_region='US')
        
        self.assertGreaterEqual(len(phones), 1)
        # Should extract at least one phone number
    
    def test_international_phone_extraction(self):
        """Test extraction of international phone numbers."""
        text = "Europe: +33 1 42 86 82 00, Algeria: +213 21 12 34 56"
        phones = extract_phones_from_text(text, default_region='FR')
        
        self.assertGreaterEqual(len(phones), 2)
    
    def test_phone_normalization_e164(self):
        """Test E.164 phone normalization."""
        # Test with valid US number
        normalized = _normalize_phone("+1 (234) 567-8900", default_region='US')
        self.assertIsNotNone(normalized)
        
        # Test with German number
        normalized = _normalize_phone("+49 30 123456", default_region='DE')
        self.assertIsNotNone(normalized)
    
    def test_phone_filtering(self):
        """Test filtering of invalid phone numbers."""
        text = "Valid: +1-234-567-8900, Invalid: 123, Invalid: 12"
        phones = extract_phones_from_text(text, default_region='US')
        
        # Should only extract valid phones (>= 7 digits)
        self.assertTrue(all(len(p.replace('+', '').replace('-', '').replace(' ', '')) >= 7 for p in phones))


class TestContactPageDiscovery(unittest.TestCase):
    """Test contact page link discovery."""
    
    def test_discover_contact_links(self):
        """Test discovery of contact page links from HTML."""
        html = """
        <html>
        <body>
            <a href="/contact">Contact Us</a>
            <a href="/about">About Company</a>
            <a href="/imprint">Imprint</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="#top">Top of Page</a>
        </body>
        </html>
        """
        base_url = "https://www.example.com"
        
        pages = discover_contact_pages(html, base_url)
        
        # Should find contact, about, imprint but not privacy
        self.assertGreaterEqual(len(pages), 3)
        self.assertTrue(any('contact' in p.lower() for p in pages))
        self.assertTrue(any('about' in p.lower() for p in pages))
        self.assertTrue(any('imprint' in p.lower() for p in pages))
        
        # Should not include privacy or anchor links
        self.assertFalse(any('privacy' in p.lower() for p in pages))
        self.assertFalse(any('#' in p for p in pages))
    
    def test_multilingual_contact_links(self):
        """Test discovery of contact links in multiple languages."""
        html = """
        <html>
        <body>
            <a href="/kontakt">Kontakt</a>
            <a href="/nous-contacter">Nous Contacter</a>
            <a href="/contacto">Contacto</a>
        </body>
        </html>
        """
        base_url = "https://www.example.de"
        
        pages = discover_contact_pages(html, base_url)
        
        # Should find all multilingual contact links
        self.assertGreaterEqual(len(pages), 3)


class TestContactExtraction(unittest.TestCase):
    """Test end-to-end contact extraction."""
    
    def test_extract_contacts_from_html(self):
        """Test extraction of all contact information from HTML."""
        html = """
        <html>
        <head><title>Company Contact</title></head>
        <body>
            <h1>Contact Us</h1>
            <p>Email: info@company.com</p>
            <p>Phone: +1-234-567-8900</p>
            <p>Alternative: sales@company.com</p>
            <nav>
                <a href="/about">About</a>
                <a href="/contact-form">Contact Form</a>
            </nav>
        </body>
        </html>
        """
        base_url = "https://www.company.com"
        
        result = extract_contacts_from_html(html, base_url, default_region='US')
        
        self.assertIsInstance(result, dict)
        self.assertIn('emails', result)
        self.assertIn('phones', result)
        self.assertIn('contact_pages', result)
        self.assertIn('has_contacts', result)
        
        # Should have found emails and phones
        self.assertGreaterEqual(len(result['emails']), 2)
        self.assertGreaterEqual(len(result['phones']), 1)
        self.assertTrue(result['has_contacts'])
    
    def test_extract_contacts_no_data(self):
        """Test extraction when no contact information available."""
        html = """
        <html>
        <body>
            <p>Just some generic content without contacts.</p>
        </body>
        </html>
        """
        base_url = "https://www.example.com"
        
        result = extract_contacts_from_html(html, base_url)
        
        self.assertEqual(len(result['emails']), 0)
        self.assertEqual(len(result['phones']), 0)
        self.assertFalse(result['has_contacts'])


class TestRegionDetection(unittest.TestCase):
    """Test country/region detection from URLs."""
    
    def test_detect_region_from_url(self):
        """Test region detection from domain TLDs."""
        test_cases = [
            ("https://www.company.de", "DE"),
            ("https://www.example.fr", "FR"),
            ("https://www.site.co.uk", "GB"),
            ("https://www.business.cn", "CN"),
            ("https://www.shop.dz", "DZ"),  # Algeria
            ("https://www.generic.com", "US"),  # Default
        ]
        
        for url, expected_region in test_cases:
            region = detect_region_from_url(url)
            self.assertEqual(region, expected_region, f"Failed for URL: {url}")


if __name__ == "__main__":
    unittest.main()
