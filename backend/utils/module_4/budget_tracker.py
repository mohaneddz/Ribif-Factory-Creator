"""
Web Call Budget Tracking
=========================

Unified tracking for all web operations with clear definitions.
Ensures budget integrity and consistent logging.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import time
from utils.logger import get_logger

logger = get_logger(__name__)

# =========================================================
# WEB CALL DEFINITIONS
# =========================================================

# DEFINITION: What counts as a "web call"
# 1. API call to search provider (Serper, Bing, DuckDuckGo, etc.) = 1 call
# 2. Page fetch/scrape for content extraction = 1 call
# 3. Image search query = 1 call
# 4. Cached result retrieval = 0 calls (no network)
#
# INVARIANT: All counters must match actual network operations

@dataclass
class WebCallTracker:
    """Tracks web calls with clear categorization."""
    
    # Search API calls
    search_queries: int = 0
    
    # Page fetches/scrapes
    pages_fetched: int = 0
    
    # Image queries
    image_queries: int = 0
    
    # Cache hits (doesn't count toward budget)
    cache_hits: int = 0
    
    # Operation timestamps for debugging
    operations: List[Dict] = field(default_factory=list)
    
    def record_search_query(self, provider: str, query: str):
        """Record a search API call."""
        self.search_queries += 1
        self.operations.append({
            'type': 'search_query',
            'provider': provider,
            'query': query,
            'timestamp': time.time()
        })
        logger.debug(f"[WEB CALL] Search query #{self.search_queries}: {provider} - {query[:50]}")
    
    def record_page_fetch(self, url: str):
        """Record a page fetch/scrape."""
        self.pages_fetched += 1
        self.operations.append({
            'type': 'page_fetch',
            'url': url,
            'timestamp': time.time()
        })
        logger.debug(f"[WEB CALL] Page fetch #{self.pages_fetched}: {url[:80]}")
    
    def record_image_query(self, provider: str, query: str):
        """Record an image search query."""
        self.image_queries += 1
        self.operations.append({
            'type': 'image_query',
            'provider': provider,
            'query': query,
            'timestamp': time.time()
        })
        logger.debug(f"[WEB CALL] Image query #{self.image_queries}: {provider} - {query[:50]}")
    
    def record_cache_hit(self, cache_key: str):
        """Record a cache hit (doesn't count toward budget)."""
        self.cache_hits += 1
        self.operations.append({
            'type': 'cache_hit',
            'key': cache_key[:50],
            'timestamp': time.time()
        })
        logger.debug(f"[CACHE HIT] #{self.cache_hits}: {cache_key[:50]}")
    
    @property
    def total_web_calls(self) -> int:
        """Total web calls (excludes cache hits)."""
        return self.search_queries + self.pages_fetched + self.image_queries
    
    def get_summary(self) -> Dict:
        """Get summary of all web operations."""
        return {
            'total_web_calls': self.total_web_calls,
            'search_queries': self.search_queries,
            'pages_fetched': self.pages_fetched,
            'image_queries': self.image_queries,
            'cache_hits': self.cache_hits,
            'breakdown': f"{self.search_queries} queries + {self.pages_fetched} pages + {self.image_queries} images = {self.total_web_calls} total"
        }
    
    def log_summary(self, context: str = ""):
        """Log a summary of web calls."""
        summary = self.get_summary()
        logger.info(f"{'['+context+'] ' if context else ''}Web Calls Summary: {summary['breakdown']}")
        logger.info(f"{'['+context+'] ' if context else ''}Cache hits: {self.cache_hits}")


@dataclass
class PerMachineBudget:
    """Budget tracker for a single machine."""
    
    machine_name: str
    max_queries: int = 1
    max_pages: int = 6
    max_llm_calls: int = 1
    timeout_seconds: float = 15.0
    
    # Actual usage
    queries_used: int = 0
    pages_fetched: int = 0
    llm_calls_used: int = 0
    
    # Timing
    start_time: float = field(default_factory=time.time)
    
    # Web call tracker
    tracker: WebCallTracker = field(default_factory=WebCallTracker)
    
    def can_query(self) -> bool:
        """Check if machine can make another search query."""
        return self.queries_used < self.max_queries
    
    def can_fetch(self) -> bool:
        """Check if machine can fetch another page."""
        return self.pages_fetched < self.max_pages
    
    def can_llm(self) -> bool:
        """Check if machine can make another LLM call."""
        return self.llm_calls_used < self.max_llm_calls
    
    def has_time(self) -> bool:
        """Check if machine has time remaining."""
        return self.time_left() > 0
    
    def time_left(self) -> float:
        """Get remaining time in seconds."""
        elapsed = time.time() - self.start_time
        return max(0, self.timeout_seconds - elapsed)
    
    def record_query(self, provider: str, query: str):
        """Record a search query."""
        self.queries_used += 1
        self.tracker.record_search_query(provider, query)
    
    def record_page_fetch(self, url: str):
        """Record a page fetch."""
        self.pages_fetched += 1
        self.tracker.record_page_fetch(url)
    
    def record_llm_call(self):
        """Record an LLM call."""
        self.llm_calls_used += 1
    
    def get_usage_summary(self) -> Dict:
        """Get budget usage summary."""
        elapsed = time.time() - self.start_time
        return {
            'machine_name': self.machine_name,
            'queries_used': f"{self.queries_used}/{self.max_queries}",
            'pages_fetched': f"{self.pages_fetched}/{self.max_pages}",
            'llm_calls_used': f"{self.llm_calls_used}/{self.max_llm_calls}",
            'time_elapsed': f"{elapsed:.1f}s",
            'web_calls_total': self.tracker.total_web_calls,
            'web_call_breakdown': self.tracker.get_summary()['breakdown'],
        }
    
    def log_usage(self):
        """Log budget usage for this machine."""
        summary = self.get_usage_summary()
        logger.info(f"Budget for '{self.machine_name}':")
        logger.info(f"  Queries: {summary['queries_used']}")
        logger.info(f"  Pages: {summary['pages_fetched']}")
        logger.info(f"  LLM calls: {summary['llm_calls_used']}")
        logger.info(f"  Time: {summary['time_elapsed']}")
        logger.info(f"  Web calls: {summary['web_call_breakdown']}")


@dataclass
class GlobalBudget:
    """Global budget tracker across all machines."""
    
    max_web_calls: int
    machines_count: int
    
    # Tracking
    web_calls_used: int = 0
    machines_processed: int = 0
    machines_skipped: int = 0
    
    # Per-machine trackers
    machine_budgets: Dict[str, PerMachineBudget] = field(default_factory=dict)
    
    # Global tracker
    global_tracker: WebCallTracker = field(default_factory=WebCallTracker)
    
    def can_allocate_machine(self) -> bool:
        """Check if we can process another machine without exceeding budget."""
        # Conservative estimate: assume max calls per machine
        estimated_calls = self.web_calls_used + 10  # Rough estimate per machine
        return estimated_calls < self.max_web_calls
    
    def create_machine_budget(
        self,
        machine_name: str,
        max_queries: int = 1,
        max_pages: int = 6,
        max_llm_calls: int = 1,
        timeout_seconds: float = 15.0
    ) -> PerMachineBudget:
        """Create a budget tracker for a machine."""
        budget = PerMachineBudget(
            machine_name=machine_name,
            max_queries=max_queries,
            max_pages=max_pages,
            max_llm_calls=max_llm_calls,
            timeout_seconds=timeout_seconds
        )
        self.machine_budgets[machine_name] = budget
        return budget
    
    def finalize_machine(self, machine_name: str):
        """Finalize a machine's budget and update global counters."""
        if machine_name not in self.machine_budgets:
            return
        
        budget = self.machine_budgets[machine_name]
        
        # Update global counters from machine tracker
        self.web_calls_used += budget.tracker.total_web_calls
        self.global_tracker.search_queries += budget.tracker.search_queries
        self.global_tracker.pages_fetched += budget.tracker.pages_fetched
        self.global_tracker.image_queries += budget.tracker.image_queries
        self.global_tracker.cache_hits += budget.tracker.cache_hits
        
        self.machines_processed += 1
        
        # Log
        budget.log_usage()
    
    def skip_machine(self, machine_name: str, reason: str):
        """Record that a machine was skipped."""
        self.machines_skipped += 1
        logger.info(f"Machine '{machine_name}' SKIPPED: {reason}")
    
    def get_global_summary(self) -> Dict:
        """Get global budget summary."""
        return {
            'machines_total': self.machines_count,
            'machines_processed': self.machines_processed,
            'machines_skipped': self.machines_skipped,
            'web_calls_used': self.web_calls_used,
            'web_calls_budget': self.max_web_calls,
            'web_calls_remaining': max(0, self.max_web_calls - self.web_calls_used),
            'budget_utilization': f"{(self.web_calls_used / self.max_web_calls * 100):.1f}%",
            'budget_compliant': self.web_calls_used <= self.max_web_calls,
            'breakdown': self.global_tracker.get_summary()['breakdown']
        }
    
    def log_global_summary(self):
        """Log global budget summary."""
        summary = self.get_global_summary()
        logger.info("=" * 70)
        logger.info("GLOBAL BUDGET SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Machines: {summary['machines_processed']}/{summary['machines_total']} processed, {summary['machines_skipped']} skipped")
        logger.info(f"Web calls: {summary['web_calls_used']}/{summary['web_calls_budget']} ({summary['budget_utilization']})")
        logger.info(f"Breakdown: {summary['breakdown']}")
        logger.info(f"Cache hits: {self.global_tracker.cache_hits}")
        logger.info(f"Budget compliance: {'✓ PASS' if summary['budget_compliant'] else '✗ FAIL'}")
        logger.info("=" * 70)
