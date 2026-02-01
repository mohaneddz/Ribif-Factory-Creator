"""
Pipeline Metrics Tracking
==========================

Consistent logging and tracking of pipeline metrics.
Separates raw extraction from post-processing metrics.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics from raw document extraction phase."""
    
    module_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Document stats
    source_file: Optional[str] = None
    source_pages: int = 0
    source_size_bytes: int = 0
    
    # Extraction results
    entities_extracted: int = 0
    fields_extracted: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    
    # Performance
    llm_calls_made: int = 0
    extraction_time_s: float = 0.0
    
    # Errors
    errors_encountered: int = 0
    warnings: List[str] = field(default_factory=list)
    
    def complete(self):
        """Mark extraction as complete."""
        self.end_time = time.time()
        self.extraction_time_s = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def log(self):
        """Log metrics."""
        logger.info(f"[{self.module_name}] RAW EXTRACTION METRICS:")
        logger.info(f"  Source: {self.source_file} ({self.source_pages} pages, {self.source_size_bytes} bytes)")
        logger.info(f"  Extracted: {self.entities_extracted} entities, {self.fields_extracted} fields")
        logger.info(f"  Confidence: avg={sum(self.confidence_scores)/len(self.confidence_scores) if self.confidence_scores else 0:.2f}")
        logger.info(f"  Performance: {self.extraction_time_s:.2f}s, {self.llm_calls_made} LLM calls")
        logger.info(f"  Quality: {self.errors_encountered} errors, {len(self.warnings)} warnings")


@dataclass
class EnrichmentMetrics:
    """Metrics from post-processing/enrichment phase."""
    
    module_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Enrichment actions
    web_searches_performed: int = 0
    web_pages_fetched: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Data quality
    fields_enriched: int = 0
    fields_estimated: int = 0
    fields_missing: int = 0
    
    # LLM usage
    llm_calls_made: int = 0
    llm_tokens_used: int = 0
    
    # Suppliers/items found
    items_found: int = 0
    suppliers_found: int = 0
    
    # Performance
    enrichment_time_s: float = 0.0
    
    # Budget tracking
    budget_queries_allowed: int = 0
    budget_queries_used: int = 0
    budget_time_allowed_s: float = 0.0
    budget_time_used_s: float = 0.0
    
    # Errors
    errors_encountered: int = 0
    quota_errors: int = 0
    
    def complete(self):
        """Mark enrichment as complete."""
        self.end_time = time.time()
        self.enrichment_time_s = self.end_time - self.start_time
        self.budget_time_used_s = self.enrichment_time_s
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def log(self):
        """Log metrics."""
        logger.info(f"[{self.module_name}] ENRICHMENT METRICS:")
        logger.info(f"  Web: {self.web_searches_performed} searches, {self.web_pages_fetched} pages")
        logger.info(f"  Cache: {self.cache_hits} hits, {self.cache_misses} misses")
        logger.info(f"  Data: {self.fields_enriched} enriched, {self.fields_estimated} estimated, {self.fields_missing} missing")
        logger.info(f"  Found: {self.items_found} items, {self.suppliers_found} suppliers")
        logger.info(f"  LLM: {self.llm_calls_made} calls, {self.llm_tokens_used} tokens")
        logger.info(f"  Budget: {self.budget_queries_used}/{self.budget_queries_allowed} queries, {self.budget_time_used_s:.1f}/{self.budget_time_allowed_s:.1f}s")
        logger.info(f"  Errors: {self.errors_encountered} total, {self.quota_errors} quota errors")


@dataclass
class FinalMetrics:
    """Final aggregated metrics for the entire pipeline."""
    
    module_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Aggregated from extraction + enrichment
    total_entities: int = 0
    total_fields: int = 0
    fields_complete: int = 0
    fields_partial: int = 0
    fields_empty: int = 0
    
    # Overall quality
    overall_confidence: str = "medium"  # low/medium/high
    confidence_score: float = 0.0
    
    # Overall performance
    total_time_s: float = 0.0
    total_llm_calls: int = 0
    total_web_searches: int = 0
    
    # Overall errors
    total_errors: int = 0
    critical_errors: int = 0
    
    # Status
    status: str = "success"  # success/partial/failed
    status_message: str = ""
    
    def complete(self):
        """Mark pipeline as complete."""
        self.end_time = time.time()
        self.total_time_s = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def log(self):
        """Log final metrics."""
        logger.info(f"[{self.module_name}] FINAL METRICS:")
        logger.info(f"  Entities: {self.total_entities} total")
        logger.info(f"  Fields: {self.total_fields} total, {self.fields_complete} complete, {self.fields_partial} partial, {self.fields_empty} empty")
        logger.info(f"  Quality: {self.overall_confidence} confidence ({self.confidence_score:.2%})")
        logger.info(f"  Performance: {self.total_time_s:.2f}s total, {self.total_llm_calls} LLM calls, {self.total_web_searches} searches")
        logger.info(f"  Status: {self.status} - {self.status_message}")
        logger.info(f"  Errors: {self.total_errors} total, {self.critical_errors} critical")


@dataclass
class PipelineMetrics:
    """Complete pipeline metrics container."""
    
    module_name: str
    extraction: Optional[ExtractionMetrics] = None
    enrichment: Optional[EnrichmentMetrics] = None
    final: Optional[FinalMetrics] = None
    
    def __post_init__(self):
        if self.extraction is None:
            self.extraction = ExtractionMetrics(module_name=self.module_name)
        if self.enrichment is None:
            self.enrichment = EnrichmentMetrics(module_name=self.module_name)
        if self.final is None:
            self.final = FinalMetrics(module_name=self.module_name)
    
    def complete_extraction(self):
        """Mark extraction phase complete and log."""
        self.extraction.complete()
        self.extraction.log()
    
    def complete_enrichment(self):
        """Mark enrichment phase complete and log."""
        self.enrichment.complete()
        self.enrichment.log()
    
    def complete_pipeline(self):
        """Mark entire pipeline complete and log."""
        # Aggregate metrics
        self.final.total_llm_calls = (
            self.extraction.llm_calls_made +
            self.enrichment.llm_calls_made
        )
        self.final.total_web_searches = self.enrichment.web_searches_performed
        self.final.total_errors = (
            self.extraction.errors_encountered +
            self.enrichment.errors_encountered
        )
        
        self.final.complete()
        self.final.log()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all metrics to dictionary."""
        return {
            "module": self.module_name,
            "extraction": self.extraction.to_dict() if self.extraction else None,
            "enrichment": self.enrichment.to_dict() if self.enrichment else None,
            "final": self.final.to_dict() if self.final else None
        }
    
    def log_all(self):
        """Log all metrics."""
        logger.info("=" * 80)
        logger.info(f"COMPLETE PIPELINE METRICS: {self.module_name}")
        logger.info("=" * 80)
        
        if self.extraction:
            self.extraction.log()
            logger.info("-" * 80)
        
        if self.enrichment:
            self.enrichment.log()
            logger.info("-" * 80)
        
        if self.final:
            self.final.log()
        
        logger.info("=" * 80)


# =========================================================
# Helper Functions
# =========================================================

def create_pipeline_metrics(module_name: str) -> PipelineMetrics:
    """Create a new pipeline metrics tracker."""
    return PipelineMetrics(module_name=module_name)


def log_metrics_summary(metrics: PipelineMetrics):
    """Log a concise summary of pipeline metrics."""
    logger.info(f"[{metrics.module_name}] Pipeline completed in {metrics.final.total_time_s:.2f}s")
    logger.info(f"  Extraction: {metrics.extraction.extraction_time_s:.2f}s, {metrics.extraction.entities_extracted} entities")
    logger.info(f"  Enrichment: {metrics.enrichment.enrichment_time_s:.2f}s, {metrics.enrichment.items_found} items")
    logger.info(f"  Quality: {metrics.final.overall_confidence} ({metrics.final.fields_complete}/{metrics.final.total_fields} complete)")
    logger.info(f"  Status: {metrics.final.status}")
