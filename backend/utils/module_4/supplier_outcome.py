"""
Supplier Outcome Tracking
===========================

INVARIANT: Every machine must have an explicit supplier outcome.
No ambiguous empty results allowed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class SupplierOutcomeStatus(Enum):
    """Explicit supplier outcome states."""
    
    # Success states
    SUPPLIERS_FOUND = "suppliers_found"  # Found 1+ suppliers
    
    # Skip states (explicit reasons why search wasn't attempted)
    SKIPPED_NO_BUDGET = "skipped_no_budget"  # Global budget exhausted
    SKIPPED_GENERIC = "skipped_generic"  # Generic/standard machine, no OEM needed
    SKIPPED_BASIC = "skipped_basic"  # Simple/basic machine, local suppliers sufficient
    SKIPPED_TIMEOUT = "skipped_timeout"  # Machine processing timed out before search
    
    # Failure states (search was attempted but failed)
    SEARCH_FAILED_API_ERROR = "search_failed_api_error"  # API/network error
    SEARCH_FAILED_NO_RESULTS = "search_failed_no_results"  # Search returned 0 results
    SEARCH_FAILED_ALL_FILTERED = "search_failed_all_filtered"  # All results filtered out
    SEARCH_FAILED_TIMEOUT = "search_failed_timeout"  # Search exceeded timeout
    SEARCH_FAILED_EXCEPTION = "search_failed_exception"  # Unexpected exception
    
    def is_success(self) -> bool:
        """Check if this is a success outcome."""
        return self == SupplierOutcomeStatus.SUPPLIERS_FOUND
    
    def is_skipped(self) -> bool:
        """Check if this is a skip outcome."""
        return self.value.startswith("skipped_")
    
    def is_failure(self) -> bool:
        """Check if this is a failure outcome."""
        return self.value.startswith("search_failed_")


@dataclass
class SupplierOutcome:
    """Complete supplier outcome for a machine."""
    
    machine_name: str
    status: SupplierOutcomeStatus
    supplier_count: int
    
    # Detailed explanation
    reason: str
    details: Optional[str] = None
    
    # Suppliers (if found)
    suppliers: List[Dict] = None
    
    # Search metadata
    queries_made: int = 0
    pages_fetched: int = 0
    candidates_evaluated: int = 0
    candidates_filtered: int = 0
    
    def __post_init__(self):
        if self.suppliers is None:
            self.suppliers = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'machine_name': self.machine_name,
            'status': self.status.value,
            'status_category': (
                'success' if self.status.is_success() else
                'skipped' if self.status.is_skipped() else
                'failed'
            ),
            'supplier_count': self.supplier_count,
            'reason': self.reason,
            'details': self.details,
            'suppliers': self.suppliers,
            'search_metadata': {
                'queries_made': self.queries_made,
                'pages_fetched': self.pages_fetched,
                'candidates_evaluated': self.candidates_evaluated,
                'candidates_filtered': self.candidates_filtered,
            }
        }
    
    def log_outcome(self):
        """Log the supplier outcome."""
        status_emoji = "✓" if self.status.is_success() else "⊘" if self.status.is_skipped() else "✗"
        
        logger.info(f"{status_emoji} Supplier outcome for '{self.machine_name}':")
        logger.info(f"  Status: {self.status.value}")
        logger.info(f"  Reason: {self.reason}")
        
        if self.status.is_success():
            logger.info(f"  Suppliers found: {self.supplier_count}")
            logger.info(f"  Queries made: {self.queries_made}, Pages fetched: {self.pages_fetched}")
            logger.info(f"  Candidates: {self.candidates_evaluated} evaluated, {self.candidates_filtered} filtered")
        elif self.status.is_failure():
            logger.info(f"  Queries made: {self.queries_made}, Pages fetched: {self.pages_fetched}")
            if self.details:
                logger.info(f"  Details: {self.details}")


class SupplierOutcomeRegistry:
    """Registry to track outcomes for all machines."""
    
    def __init__(self, total_machines: int):
        self.total_machines = total_machines
        self.outcomes: Dict[str, SupplierOutcome] = {}
    
    def record_outcome(self, outcome: SupplierOutcome):
        """Record an outcome for a machine."""
        self.outcomes[outcome.machine_name] = outcome
        outcome.log_outcome()
    
    def record_success(
        self,
        machine_name: str,
        suppliers: List[Dict],
        queries_made: int = 0,
        pages_fetched: int = 0,
        candidates_evaluated: int = 0,
        candidates_filtered: int = 0
    ):
        """Record a successful supplier search."""
        outcome = SupplierOutcome(
            machine_name=machine_name,
            status=SupplierOutcomeStatus.SUPPLIERS_FOUND,
            supplier_count=len(suppliers),
            reason=f"Found {len(suppliers)} supplier(s) after filtering",
            suppliers=suppliers,
            queries_made=queries_made,
            pages_fetched=pages_fetched,
            candidates_evaluated=candidates_evaluated,
            candidates_filtered=candidates_filtered
        )
        self.record_outcome(outcome)
    
    def record_skip(
        self,
        machine_name: str,
        status: SupplierOutcomeStatus,
        reason: str,
        details: Optional[str] = None
    ):
        """Record a skipped supplier search."""
        if not status.is_skipped():
            raise ValueError(f"Status must be a skip status, got {status}")
        
        outcome = SupplierOutcome(
            machine_name=machine_name,
            status=status,
            supplier_count=0,
            reason=reason,
            details=details,
            suppliers=[]
        )
        self.record_outcome(outcome)
    
    def record_failure(
        self,
        machine_name: str,
        status: SupplierOutcomeStatus,
        reason: str,
        details: Optional[str] = None,
        queries_made: int = 0,
        pages_fetched: int = 0,
        candidates_evaluated: int = 0,
        candidates_filtered: int = 0
    ):
        """Record a failed supplier search."""
        if not status.is_failure():
            raise ValueError(f"Status must be a failure status, got {status}")
        
        outcome = SupplierOutcome(
            machine_name=machine_name,
            status=status,
            supplier_count=0,
            reason=reason,
            details=details,
            suppliers=[],
            queries_made=queries_made,
            pages_fetched=pages_fetched,
            candidates_evaluated=candidates_evaluated,
            candidates_filtered=candidates_filtered
        )
        self.record_outcome(outcome)
    
    def get_summary(self) -> Dict:
        """Get summary of all outcomes."""
        success_count = sum(1 for o in self.outcomes.values() if o.status.is_success())
        skipped_count = sum(1 for o in self.outcomes.values() if o.status.is_skipped())
        failed_count = sum(1 for o in self.outcomes.values() if o.status.is_failure())
        
        total_suppliers = sum(o.supplier_count for o in self.outcomes.values())
        
        return {
            'total_machines': self.total_machines,
            'machines_with_outcome': len(self.outcomes),
            'machines_missing_outcome': self.total_machines - len(self.outcomes),
            'success': success_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'total_suppliers_found': total_suppliers,
            'all_machines_have_outcome': len(self.outcomes) == self.total_machines
        }
    
    def log_summary(self):
        """Log summary of all outcomes."""
        summary = self.get_summary()
        
        logger.info("=" * 70)
        logger.info("SUPPLIER OUTCOME SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Machines: {summary['machines_with_outcome']}/{summary['total_machines']} have explicit outcomes")
        
        if summary['machines_missing_outcome'] > 0:
            logger.warning(f"⚠ {summary['machines_missing_outcome']} machines have NO OUTCOME (BUG!)")
        
        logger.info(f"Success: {summary['success']} machines with suppliers")
        logger.info(f"Skipped: {summary['skipped']} machines skipped (valid reasons)")
        logger.info(f"Failed: {summary['failed']} machines failed search")
        logger.info(f"Total suppliers: {summary['total_suppliers_found']}")
        logger.info(f"Outcome compliance: {'✓ PASS' if summary['all_machines_have_outcome'] else '✗ FAIL'}")
        logger.info("=" * 70)
    
    def validate(self) -> bool:
        """Validate that all machines have outcomes."""
        summary = self.get_summary()
        if not summary['all_machines_have_outcome']:
            missing = self.total_machines - len(self.outcomes)
            logger.error(f"VALIDATION FAILED: {missing} machines missing explicit supplier outcome!")
            return False
        return True
