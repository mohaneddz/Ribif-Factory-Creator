"""
Centralized External Client Configuration
==========================================

All external service URLs, client initialization, and connection management
happen here. Ensures consistent URL normalization and configuration.
"""

import os
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from utils.logger import get_logger

logger = get_logger(__name__)


# =========================================================
# URL Normalization
# =========================================================

def normalize_base_url(url: str, ensure_trailing_slash: bool = True) -> str:
    """
    Normalize a base URL consistently.
    
    Args:
        url: Base URL to normalize
        ensure_trailing_slash: Add trailing slash if missing
        
    Returns:
        Normalized URL
        
    Examples:
        normalize_base_url("https://api.example.com") -> "https://api.example.com/"
        normalize_base_url("http://localhost:5000/") -> "http://localhost:5000/"
    """
    if not url:
        return ""
    
    # Strip whitespace
    url = url.strip()
    
    # Ensure protocol
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # Parse and normalize
    parsed = urlparse(url)
    
    # Remove duplicate slashes in path
    path = parsed.path
    while '//' in path:
        path = path.replace('//', '/')
    
    # Add trailing slash if needed
    if ensure_trailing_slash and not path.endswith('/'):
        path += '/'
    
    # Reconstruct
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    
    if parsed.params:
        normalized += f";{parsed.params}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    if parsed.fragment:
        normalized += f"#{parsed.fragment}"
    
    return normalized


def build_endpoint_url(base_url: str, endpoint: str) -> str:
    """
    Safely join base URL with endpoint.
    
    Examples:
        build_endpoint_url("https://api.com/", "users") -> "https://api.com/users"
        build_endpoint_url("https://api.com", "/users") -> "https://api.com/users"
    """
    base = normalize_base_url(base_url, ensure_trailing_slash=True)
    endpoint = endpoint.lstrip('/')
    return urljoin(base, endpoint)


# =========================================================
# External Service Configuration
# =========================================================

class ExternalServiceConfig:
    """Centralized configuration for all external services."""
    
    def __init__(self):
        # Supabase
        self.supabase_url = normalize_base_url(
            os.getenv("SUPABASE_URL", ""),
            ensure_trailing_slash=False
        )
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        
        # Storage
        self.storage_base_url = normalize_base_url(
            os.getenv("STORAGE_BASE_URL", self.supabase_url),
            ensure_trailing_slash=True
        )
        
        # Backend API
        self.backend_base_url = normalize_base_url(
            os.getenv("BACKEND_BASE_URL", "http://localhost:5000"),
            ensure_trailing_slash=True
        )
        
        # Frontend
        self.frontend_base_url = normalize_base_url(
            os.getenv("FRONTEND_BASE_URL", "http://localhost:3000"),
            ensure_trailing_slash=True
        )
        
        # External APIs
        self.serper_api_key = os.getenv("SERPER_API_KEY", "")
        self.bing_api_key = os.getenv("BING_API_KEY", "")
        
        # Vertex AI
        self.vertex_project = os.getenv("VERTEX_PROJECT", "")
        self.vertex_location = os.getenv("VERTEX_LOCATION", "us-central1")
        
        # Rate limiting
        self.rate_limit_delay = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        logger.info("External service configuration initialized")
        self._log_config()
    
    def _log_config(self):
        """Log configuration (without sensitive data)."""
        logger.info(f"Supabase URL: {self.supabase_url}")
        logger.info(f"Storage URL: {self.storage_base_url}")
        logger.info(f"Backend URL: {self.backend_base_url}")
        logger.info(f"Serper API: {'Configured' if self.serper_api_key else 'Not configured'}")
        logger.info(f"Bing API: {'Configured' if self.bing_api_key else 'Not configured'}")
    
    def get_supabase_endpoint(self, path: str) -> str:
        """Build Supabase API endpoint."""
        return build_endpoint_url(self.supabase_url, path)
    
    def get_storage_url(self, bucket: str, path: str) -> str:
        """Build storage URL."""
        return build_endpoint_url(
            self.storage_base_url,
            f"storage/v1/object/public/{bucket}/{path}"
        )
    
    def get_backend_endpoint(self, path: str) -> str:
        """Build backend API endpoint."""
        return build_endpoint_url(self.backend_base_url, path)
    
    def is_supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_key)
    
    def is_search_configured(self) -> bool:
        """Check if any search API is configured."""
        return bool(self.serper_api_key or self.bing_api_key)


# Singleton instance
_config: Optional[ExternalServiceConfig] = None


def get_external_config() -> ExternalServiceConfig:
    """Get the singleton external service configuration."""
    global _config
    if _config is None:
        _config = ExternalServiceConfig()
    return _config


def reset_external_config():
    """Reset configuration (useful for testing)."""
    global _config
    _config = None


# =========================================================
# Client Initialization Helpers
# =========================================================

def get_supabase_client():
    """
    Get initialized Supabase client.
    Uses centralized configuration.
    """
    from supabase_utils import get_supabase
    return get_supabase()


def get_http_headers(include_auth: bool = False) -> Dict[str, str]:
    """
    Get standard HTTP headers for API calls.
    
    Args:
        include_auth: Include Supabase auth header
        
    Returns:
        Headers dict
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "RIBIF-Backend/1.0"
    }
    
    if include_auth:
        config = get_external_config()
        if config.supabase_key:
            headers["apikey"] = config.supabase_key
            headers["Authorization"] = f"Bearer {config.supabase_key}"
    
    return headers


# =========================================================
# Validation
# =========================================================

def validate_external_services() -> Dict[str, bool]:
    """
    Validate all external service configurations.
    
    Returns:
        Dict of service_name -> is_valid
    """
    config = get_external_config()
    
    return {
        "supabase": config.is_supabase_configured(),
        "storage": bool(config.storage_base_url),
        "backend": bool(config.backend_base_url),
        "search_apis": config.is_search_configured(),
        "vertex_ai": bool(config.vertex_project),
    }


def get_service_status() -> Dict[str, Any]:
    """
    Get detailed status of all external services.
    
    Returns:
        Status dictionary
    """
    validation = validate_external_services()
    config = get_external_config()
    
    return {
        "services": validation,
        "all_configured": all(validation.values()),
        "urls": {
            "supabase": config.supabase_url,
            "storage": config.storage_base_url,
            "backend": config.backend_base_url,
            "frontend": config.frontend_base_url,
        },
        "rate_limiting": {
            "delay": config.rate_limit_delay,
            "max_retries": config.max_retries,
        }
    }
