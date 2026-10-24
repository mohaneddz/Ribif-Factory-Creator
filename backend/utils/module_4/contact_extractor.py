"""
Contact Extraction Utilities for Module 4 Supplier Enrichment

Provides robust contact information extraction from supplier web pages including:
- Email addresses (with normalization and deduplication)
- Phone numbers (with E.164 formatting when possible)
- Contact page discovery (About/Contact/Imprint links)
- Budget-aware page fetching (max 1 extra page per supplier)
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
import phonenumbers
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================================================
# REGEX PATTERNS
# ============================================================================

# Email pattern - comprehensive but conservative
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9][\w\.\-\+]*@(?:[A-Za-z0-9][\w\-]*\.)+[A-Za-z]{2,}\b',
    re.IGNORECASE
)

# Phone patterns - international formats
# Matches: +1-234-567-8900, (123) 456-7890, +33 1 42 86 82 00, etc.
PHONE_PATTERN = re.compile(
    r'(?:\+\d{1,4}[\s\-\.]?)?'  # Optional country code
    r'(?:\(\d{1,4}\)[\s\-\.]?)?'  # Optional area code in parens
    r'\d{1,4}[\s\-\.\(\)]*'  # First group
    r'\d{1,4}[\s\-\.\(\)]*'  # Second group
    r'\d{1,9}'  # Final group
)

# Contact page link patterns (case-insensitive)
CONTACT_KEYWORDS = [
    'contact', 'about', 'imprint', 'impressum', 'legal', 'company',
    'support', 'get-in-touch', 'reach-us', 'kontakt', 'nous-contacter',
    'contacto', 'contatto', 'unternehmen', 'empresa'
]

# Avoid these pages when looking for contacts
AVOID_KEYWORDS = [
    'privacy', 'terms', 'cookie', 'legal-notice', 'disclaimer',
    'sitemap', 'search', 'cart', 'checkout', 'login', 'register'
]


# ============================================================================
# EMAIL EXTRACTION & NORMALIZATION
# ============================================================================

def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract and normalize email addresses from text.
    
    Args:
        text: HTML or plain text content
        
    Returns:
        List of normalized (lowercase, deduped) email addresses
    """
    if not text:
        return []
    
    # Find all email matches
    raw_emails = EMAIL_PATTERN.findall(text)
    
    # Normalize and filter
    normalized = set()
    for email in raw_emails:
        email_lower = email.lower().strip()
        
        # Filter out common false positives
        if _is_valid_email(email_lower):
            normalized.add(email_lower)
    
    return sorted(list(normalized))


def _is_valid_email(email: str) -> bool:
    """
    Validate email to filter false positives.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email looks legitimate
    """
    # Filter out image files and common false positives
    invalid_patterns = [
        r'\.png@', r'\.jpg@', r'\.gif@', r'\.svg@',
        r'\.ico@', r'example\.com$', r'test\.com$',
        r'domain\.com$', r'yourcompany\.com$'
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, email, re.IGNORECASE):
            return False
    
    # Must have reasonable length
    if len(email) < 5 or len(email) > 254:
        return False
    
    # Must have proper format
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    local, domain = parts
    if not local or not domain or '.' not in domain:
        return False
    
    return True


# ============================================================================
# PHONE EXTRACTION & NORMALIZATION
# ============================================================================

def extract_phones_from_text(text: str, default_region: str = 'US') -> List[str]:
    """
    Extract and normalize phone numbers from text.
    
    Attempts E.164 formatting when possible, otherwise returns cleaned raw format.
    
    Args:
        text: HTML or plain text content
        default_region: Default country code for parsing (e.g., 'US', 'DE', 'CN')
        
    Returns:
        List of normalized phone numbers (deduped)
    """
    if not text:
        return []
    
    # Find all phone-like strings
    raw_phones = PHONE_PATTERN.findall(text)
    
    normalized = set()
    for phone in raw_phones:
        cleaned = _normalize_phone(phone.strip(), default_region)
        if cleaned:
            normalized.add(cleaned)
    
    return sorted(list(normalized))


def _normalize_phone(phone: str, default_region: str = 'US') -> Optional[str]:
    """
    Normalize phone number to E.164 format if possible, else clean format.
    
    Args:
        phone: Raw phone string
        default_region: Default country for parsing
        
    Returns:
        Normalized phone number or None if invalid
    """
    if not phone or len(phone) < 7:
        return None
    
    # Remove common non-digit characters for validation
    digits_only = re.sub(r'[^\d+]', '', phone)
    
    # Must have at least 7 digits (minimum valid phone)
    if len(re.sub(r'\D', '', digits_only)) < 7:
        return None
    
    # Attempt E.164 parsing using phonenumbers library
    try:
        parsed = phonenumbers.parse(phone, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        pass
    
    # Fallback: return cleaned format (remove extra spaces, keep +/digits/parens/dashes)
    cleaned = re.sub(r'\s+', ' ', phone.strip())
    cleaned = re.sub(r'[^\d\+\-\(\)\s]', '', cleaned)
    
    # Final sanity check
    if len(re.sub(r'\D', '', cleaned)) >= 7:
        return cleaned
    
    return None


# ============================================================================
# CONTACT PAGE DISCOVERY
# ============================================================================

def discover_contact_pages(html: str, base_url: str, max_candidates: int = 5) -> List[str]:
    """
    Find contact/about/imprint page URLs from HTML.
    
    Args:
        html: HTML content of supplier page
        base_url: Base URL for resolving relative links
        max_candidates: Maximum contact pages to return
        
    Returns:
        List of absolute URLs to potential contact pages
    """
    if not html or not base_url:
        return []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        candidates = []
        seen_urls = set()
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Get link text
            link_text = link.get_text(strip=True).lower()
            href_lower = href.lower()
            
            # Check if link contains contact keywords
            has_contact_keyword = any(kw in link_text or kw in href_lower for kw in CONTACT_KEYWORDS)
            has_avoid_keyword = any(kw in href_lower for kw in AVOID_KEYWORDS)
            
            if has_contact_keyword and not has_avoid_keyword:
                # Resolve to absolute URL
                absolute_url = urljoin(base_url, href)
                
                # Dedupe and ensure same domain
                if absolute_url not in seen_urls and _is_same_domain(base_url, absolute_url):
                    candidates.append(absolute_url)
                    seen_urls.add(absolute_url)
                    
                    if len(candidates) >= max_candidates:
                        break
        
        return candidates
    
    except Exception as e:
        logger.warning(f"Error discovering contact pages from {base_url}: {e}")
        return []


def _is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs share the same domain."""
    try:
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        
        # Remove 'www.' prefix for comparison
        domain1 = domain1.replace('www.', '')
        domain2 = domain2.replace('www.', '')
        
        return domain1 == domain2
    except:
        return False


# ============================================================================
# MAIN EXTRACTION INTERFACE
# ============================================================================

def extract_contacts_from_html(
    html: str,
    base_url: str,
    default_region: str = 'US'
) -> Dict[str, any]:
    """
    Extract all contact information from HTML content.
    
    Args:
        html: HTML content
        base_url: Base URL for context
        default_region: Default country for phone parsing
        
    Returns:
        Dictionary with:
        - emails: List[str]
        - phones: List[str]
        - contact_pages: List[str]
        - has_contacts: bool
    """
    if not html:
        return {
            'emails': [],
            'phones': [],
            'contact_pages': [],
            'has_contacts': False
        }
    
    # Extract from main page
    emails = extract_emails_from_text(html)
    phones = extract_phones_from_text(html, default_region)
    contact_pages = discover_contact_pages(html, base_url)
    
    return {
        'emails': emails,
        'phones': phones,
        'contact_pages': contact_pages,
        'has_contacts': bool(emails or phones)
    }


def fetch_and_extract_contacts(
    page_url: str,
    html: str,
    budget_tracker,
    default_region: str = 'US',
    max_contact_pages: int = 1
) -> Dict[str, any]:
    """
    Extract contacts from a supplier page, optionally fetching 1 contact page.
    
    This is the main entry point for contact extraction with budget awareness.
    
    Args:
        page_url: URL of the supplier page
        html: HTML content of supplier page
        budget_tracker: BudgetTracker instance for budget enforcement
        default_region: Default country for phone parsing
        max_contact_pages: Max additional pages to fetch (default 1)
        
    Returns:
        Dictionary with:
        - emails: List[str]
        - phones: List[str]
        - contact_pages: List[str]
        - has_contacts: bool
    """
    # Extract from main page first
    result = extract_contacts_from_html(html, page_url, default_region)
    
    # If we already have contacts, no need to fetch more
    if result['has_contacts']:
        logger.debug(f"Found contacts on main page: {page_url}")
        return result
    
    # If no contacts and we have discovered contact pages, try fetching ONE
    if result['contact_pages'] and max_contact_pages > 0:
        contact_page_url = result['contact_pages'][0]
        
        # Check budget before fetching
        if budget_tracker.can_fetch_page():
            try:
                from utils.module_4.search_and_fetch import fetch_page_content
                
                contact_html = fetch_page_content(contact_page_url)
                if contact_html:
                    budget_tracker.record_page_fetch()
                    
                    # Extract from contact page
                    contact_result = extract_contacts_from_html(
                        contact_html,
                        contact_page_url,
                        default_region
                    )
                    
                    # Merge results (dedupe)
                    result['emails'] = sorted(list(set(result['emails'] + contact_result['emails'])))
                    result['phones'] = sorted(list(set(result['phones'] + contact_result['phones'])))
                    result['has_contacts'] = bool(result['emails'] or result['phones'])
                    
                    logger.info(f"Fetched contact page and found: {len(result['emails'])} emails, {len(result['phones'])} phones")
            
            except Exception as e:
                logger.warning(f"Failed to fetch contact page {contact_page_url}: {e}")
    
    return result


# ============================================================================
# REGION DETECTION (Helper for better phone parsing)
# ============================================================================

def detect_region_from_url(url: str) -> str:
    """
    Detect likely country/region from URL domain for better phone parsing.
    
    Args:
        url: Website URL
        
    Returns:
        ISO country code (e.g., 'US', 'DE', 'CN')
    """
    if not url:
        return 'US'
    
    domain_to_region = {
        '.de': 'DE', '.fr': 'FR', '.uk': 'GB', '.co.uk': 'GB',
        '.it': 'IT', '.es': 'ES', '.nl': 'NL', '.be': 'BE',
        '.cn': 'CN', '.jp': 'JP', '.kr': 'KR', '.in': 'IN',
        '.ca': 'CA', '.au': 'AU', '.br': 'BR', '.mx': 'MX',
        '.dz': 'DZ',  # Algeria
    }
    
    url_lower = url.lower()
    for tld, region in domain_to_region.items():
        if tld in url_lower:
            return region
    
    return 'US'  # Default
