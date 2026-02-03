"""
Quota and Rate Limit Management
================================

Graceful handling of API quotas, rate limits, and external service errors.
Prevents wasting retries and provides clean user-facing error messages.
"""

import time
import functools
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)


# =========================================================
# Error Detection
# =========================================================

QUOTA_ERROR_PATTERNS = [
    "quota exceeded",
    "rate limit",
    "too many requests",
    "429",
    "insufficient credits",
    "quota",
    "limit reached",
    "throttled",
    "resource exhausted",
]


def is_quota_error(error: Exception) -> bool:
    """
    Detect if an error is quota/rate-limit related.
    
    Args:
        error: Exception to check
        
    Returns:
        True if quota/rate-limit error
    """
    error_str = str(error).lower()
    return any(pattern in error_str for pattern in QUOTA_ERROR_PATTERNS)


def is_auth_error(error: Exception) -> bool:
    """Detect if error is authentication-related."""
    error_str = str(error).lower()
    auth_patterns = ["unauthorized", "401", "403", "forbidden", "authentication", "api key"]
    return any(pattern in error_str for pattern in auth_patterns)


# =========================================================
# Quota Tracker
# =========================================================

@dataclass
class QuotaTracker:
    """Track quota usage for a service."""
    
    service_name: str
    max_calls: int = 1000
    calls_made: int = 0
    errors_encountered: int = 0
    quota_exhausted: bool = False
    last_error: Optional[str] = None
    error_timestamp: Optional[float] = None
    
    def can_call(self) -> bool:
        """Check if service can be called."""
        if self.quota_exhausted:
            return False
        return self.calls_made < self.max_calls
    
    def record_call(self):
        """Record a successful call."""
        self.calls_made += 1
    
    def record_error(self, error: Exception):
        """Record an error."""
        self.errors_encountered += 1
        self.last_error = str(error)
        self.error_timestamp = time.time()
        
        if is_quota_error(error):
            self.quota_exhausted = True
            logger.warning(f"Quota exhausted for {self.service_name}: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "service": self.service_name,
            "calls_made": self.calls_made,
            "max_calls": self.max_calls,
            "quota_exhausted": self.quota_exhausted,
            "errors": self.errors_encountered,
            "last_error": self.last_error,
            "can_call": self.can_call()
        }


# Global quota trackers
_quota_trackers: Dict[str, QuotaTracker] = {}


def get_quota_tracker(service_name: str, max_calls: int = 1000) -> QuotaTracker:
    """Get or create a quota tracker for a service."""
    if service_name not in _quota_trackers:
        _quota_trackers[service_name] = QuotaTracker(service_name, max_calls)
    return _quota_trackers[service_name]


def reset_quota_tracker(service_name: str = None):
    """Reset quota tracker(s)."""
    if service_name:
        _quota_trackers.pop(service_name, None)
    else:
        _quota_trackers.clear()


# =========================================================
# Rate Limiting
# =========================================================

@dataclass
class RateLimiter:
    """Simple rate limiter with exponential backoff."""
    
    min_delay: float = 0.5
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    last_call_time: float = 0
    current_delay: float = field(init=False)
    
    def __post_init__(self):
        self.current_delay = self.min_delay
    
    def wait(self):
        """Wait if needed to respect rate limit."""
        if self.last_call_time > 0:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.current_delay:
                sleep_time = self.current_delay - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def record_success(self):
        """Record successful call - reset delay."""
        self.current_delay = self.min_delay
    
    def record_failure(self):
        """Record failed call - increase delay."""
        self.current_delay = min(
            self.current_delay * self.backoff_factor,
            self.max_delay
        )
        logger.debug(f"Backoff increased to {self.current_delay:.2f}s")


# Global rate limiters
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(service_name: str, min_delay: float = 0.5) -> RateLimiter:
    """Get or create a rate limiter for a service."""
    if service_name not in _rate_limiters:
        _rate_limiters[service_name] = RateLimiter(min_delay=min_delay)
    return _rate_limiters[service_name]


# =========================================================
# Decorators
# =========================================================

def with_quota_check(service_name: str, max_calls: int = 1000):
    """
    Decorator to check quota before calling a function.
    
    Usage:
        @with_quota_check("vertex_ai", max_calls=100)
        def call_vertex_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_quota_tracker(service_name, max_calls)
            
            if not tracker.can_call():
                error_msg = f"Quota exhausted for {service_name}"
                if tracker.last_error:
                    error_msg += f": {tracker.last_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            try:
                result = func(*args, **kwargs)
                tracker.record_call()
                return result
            except Exception as e:
                tracker.record_error(e)
                if tracker.quota_exhausted:
                    # Don't retry if quota exhausted
                    raise RuntimeError(f"Quota exhausted for {service_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


def with_rate_limit(service_name: str, min_delay: float = 0.5):
    """
    Decorator to add rate limiting to a function.
    
    Usage:
        @with_rate_limit("serper_api", min_delay=1.0)
        def search_serper(query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(service_name, min_delay)
            limiter.wait()
            
            try:
                result = func(*args, **kwargs)
                limiter.record_success()
                return result
            except Exception as e:
                if is_quota_error(e):
                    limiter.record_failure()
                raise
        
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    backoff: bool = True,
    catch_quota_errors: bool = True,
    initial_wait: float = 2.0,
    max_wait: float = 120.0
):
    """
    Decorator to retry a function with exponential backoff.
    For 429/rate limit errors, uses longer initial wait (30s).
    Stops retrying on persistent quota errors.
    
    Usage:
        @with_retry(max_attempts=3, backoff=True)
        def unstable_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check for 429 rate limit specifically
                    is_429 = "429" in error_str or "resource_exhausted" in error_str
                    
                    # Don't retry persistent quota errors (but DO retry 429 rate limits)
                    if catch_quota_errors and is_quota_error(e) and not is_429:
                        logger.warning(f"Quota error detected, stopping retries: {e}")
                        raise
                    
                    # Don't retry auth errors
                    if is_auth_error(e):
                        logger.warning(f"Auth error detected, stopping retries: {e}")
                        raise
                    
                    if attempt < max_attempts - 1:
                        if backoff:
                            # For 429 errors, use longer initial wait (30s minimum)
                            if is_429:
                                sleep_time = min(30 * (2 ** attempt), max_wait)  # 30s, 60s, 120s
                                logger.warning(f"Rate limit 429, waiting {sleep_time}s before retry {attempt + 2}/{max_attempts}")
                            else:
                                sleep_time = min(initial_wait * (2 ** attempt), max_wait)
                                logger.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s: {e}")
                            time.sleep(sleep_time)
                        else:
                            logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator


# =========================================================
# Context Manager
# =========================================================

class QuotaContext:
    """Context manager for quota-aware operations."""
    
    def __init__(self, service_name: str, max_calls: int = 1000):
        self.service_name = service_name
        self.max_calls = max_calls
        self.tracker = None
    
    def __enter__(self):
        self.tracker = get_quota_tracker(self.service_name, self.max_calls)
        
        if not self.tracker.can_call():
            raise RuntimeError(f"Quota exhausted for {self.service_name}")
        
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.tracker.record_error(exc_val)
            # Suppress quota errors if already logged
            if self.tracker.quota_exhausted:
                return True
        else:
            self.tracker.record_call()
        return False


# =========================================================
# User-Facing Error Messages
# =========================================================

def get_user_friendly_error(error: Exception) -> Dict[str, Any]:
    """
    Convert technical error to user-friendly message.
    
    Returns:
        {
            "error": "short_code",
            "message": "user-friendly message",
            "suggestion": "what user can do",
            "technical_details": "original error (optional)"
        }
    """
    error_str = str(error).lower()
    
    if is_quota_error(error):
        return {
            "error": "quota_exceeded",
            "message": "API quota or rate limit exceeded",
            "suggestion": "Please wait a few minutes and try again, or contact support to increase limits",
            "technical_details": str(error)[:200]
        }
    
    if is_auth_error(error):
        return {
            "error": "authentication_failed",
            "message": "Authentication failed for external service",
            "suggestion": "Please check API keys in configuration",
            "technical_details": str(error)[:200]
        }
    
    if "timeout" in error_str or "timed out" in error_str:
        return {
            "error": "timeout",
            "message": "Request timed out",
            "suggestion": "The service is taking longer than expected. Please try again",
            "technical_details": str(error)[:200]
        }
    
    if "connection" in error_str or "network" in error_str:
        return {
            "error": "connection_error",
            "message": "Network connection error",
            "suggestion": "Please check your internet connection and try again",
            "technical_details": str(error)[:200]
        }
    
    # Generic error
    return {
        "error": "unknown_error",
        "message": "An unexpected error occurred",
        "suggestion": "Please try again or contact support if the problem persists",
        "technical_details": str(error)[:200]
    }


# =========================================================
# Status Reporting
# =========================================================

def get_all_quota_status() -> Dict[str, Any]:
    """Get status of all quota trackers."""
    return {
        name: tracker.get_status()
        for name, tracker in _quota_trackers.items()
    }


def get_service_health() -> Dict[str, Any]:
    """Get overall service health based on quotas."""
    all_status = get_all_quota_status()
    
    total_services = len(all_status)
    exhausted_services = sum(1 for s in all_status.values() if s["quota_exhausted"])
    
    return {
        "total_services": total_services,
        "healthy_services": total_services - exhausted_services,
        "exhausted_services": exhausted_services,
        "services": all_status,
        "overall_health": "healthy" if exhausted_services == 0 else "degraded"
    }
