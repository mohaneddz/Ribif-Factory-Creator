"""
Global Budget Controller - Hard Budget Enforcement
===================================================

Thread-safe atomic budget controller for DETERMINISTIC budget enforcement.
NO MORE SOFT LIMITS - budgets are HARD STOPS enforced before any web call.

Design:
- Single source of truth for remaining budget
- Atomic reserve/consume/release operations (thread-safe)
- Blocks operations when budget exhausted
- Integrates with all web calls (search queries, page fetches)
"""

import threading
from dataclasses import dataclass, field
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GlobalBudgetController:
    """
    Thread-safe global budget controller with atomic operations.
    
    INVARIANTS:
    1. consumed + reserved <= max_budget (ALWAYS)
    2. consumed never decreases (monotonic)
    3. All web calls MUST reserve budget BEFORE execution
    4. Failed operations MUST release reserved budget
    """
    
    max_budget: int  # Hard limit (e.g., 135)
    
    # Actual consumed budget (completed operations)
    _consumed: int = 0
    
    # Reserved budget (operations in progress)
    _reserved: int = 0
    
    # Thread-safety
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    # Operation tracking
    _operations: list = field(default_factory=list)
    
    def remaining(self) -> int:
        """Get remaining budget available for NEW reservations."""
        with self._lock:
            return max(0, self.max_budget - self._consumed - self._reserved)
    
    def consumed(self) -> int:
        """Get total consumed budget (completed operations)."""
        with self._lock:
            return self._consumed
    
    def reserved(self) -> int:
        """Get currently reserved budget (operations in flight)."""
        with self._lock:
            return self._reserved
    
    def can_reserve(self, n: int) -> bool:
        """Check if we can reserve n calls without exceeding budget."""
        with self._lock:
            return (self._consumed + self._reserved + n) <= self.max_budget
    
    def reserve_calls(self, n: int, description: str = "") -> bool:
        """
        Atomically reserve n calls. Returns True if reservation successful.
        
        MUST be called BEFORE any web operation.
        If returns False, the operation should be skipped/aborted.
        
        Args:
            n: Number of calls to reserve
            description: Optional description for logging
            
        Returns:
            True if reserved, False if budget insufficient
        """
        with self._lock:
            if (self._consumed + self._reserved + n) <= self.max_budget:
                self._reserved += n
                logger.debug(f"[BUDGET] Reserved {n} calls ({description}) - "
                           f"Consumed: {self._consumed}, Reserved: {self._reserved}, "
                           f"Remaining: {self.max_budget - self._consumed - self._reserved}")
                return True
            else:
                logger.warning(f"[BUDGET] Cannot reserve {n} calls ({description}) - "
                             f"Would exceed budget. Consumed: {self._consumed}, "
                             f"Reserved: {self._reserved}, Max: {self.max_budget}")
                return False
    
    def consume_call(self, description: str = "") -> None:
        """
        Mark 1 reserved call as consumed (completed).
        
        MUST be called AFTER each successful web operation.
        Moves 1 from reserved → consumed.
        
        Args:
            description: Optional description for tracking
        """
        with self._lock:
            if self._reserved > 0:
                self._reserved -= 1
                self._consumed += 1
                self._operations.append({
                    'type': 'consume',
                    'description': description,
                    'consumed_total': self._consumed
                })
                logger.debug(f"[BUDGET] Consumed 1 call ({description}) - "
                           f"Total consumed: {self._consumed}, Reserved: {self._reserved}")
            else:
                # This should not happen - indicates a bug
                logger.error(f"[BUDGET] BUG: Attempted to consume call without reservation! "
                           f"Description: {description}")
                # Increment consumed anyway to track the overshoot
                self._consumed += 1
    
    def release_calls(self, n: int, reason: str = "") -> None:
        """
        Release n reserved calls (operation failed/cancelled).
        
        MUST be called if a reserved operation fails or is cancelled.
        Returns budget to available pool.
        
        Args:
            n: Number of calls to release
            reason: Why the calls are being released
        """
        with self._lock:
            release_amount = min(n, self._reserved)
            self._reserved -= release_amount
            logger.debug(f"[BUDGET] Released {release_amount} calls ({reason}) - "
                       f"Consumed: {self._consumed}, Reserved: {self._reserved}")
            
            if release_amount < n:
                logger.warning(f"[BUDGET] Tried to release {n} calls but only {release_amount} "
                             f"were reserved - possible bug")
    
    def get_summary(self) -> dict:
        """Get budget summary for reporting."""
        with self._lock:
            return {
                'max_budget': self.max_budget,
                'consumed': self._consumed,
                'reserved': self._reserved,
                'remaining': self.max_budget - self._consumed - self._reserved,
                'utilization_pct': round((self._consumed / self.max_budget) * 100, 1),
                'compliant': self._consumed <= self.max_budget,
                'overshoot': max(0, self._consumed - self.max_budget)
            }
    
    def log_summary(self) -> None:
        """Log budget summary."""
        summary = self.get_summary()
        status = "✓ PASS" if summary['compliant'] else "✗ FAIL (OVERSHOOT)"
        
        logger.info("=" * 70)
        logger.info("GLOBAL BUDGET ENFORCEMENT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Budget: {summary['consumed']}/{summary['max_budget']} "
                   f"({summary['utilization_pct']}% utilized)")
        logger.info(f"Reserved (in-flight): {summary['reserved']}")
        logger.info(f"Remaining: {summary['remaining']}")
        logger.info(f"Compliance: {status}")
        if summary['overshoot'] > 0:
            logger.error(f"⚠️  OVERSHOOT: {summary['overshoot']} calls exceeded budget!")
        logger.info("=" * 70)
    
    def assert_compliance(self) -> None:
        """Assert that budget was not exceeded. Raises AssertionError if failed."""
        summary = self.get_summary()
        assert summary['consumed'] <= summary['max_budget'], (
            f"Budget exceeded! Consumed {summary['consumed']} > Max {summary['max_budget']} "
            f"(overshoot: {summary['overshoot']})"
        )
        logger.info(f"✓ Budget compliance verified: {summary['consumed']}/{summary['max_budget']}")
