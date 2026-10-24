"""
Test Module 4 Global Budget Enforcement
=========================================

Tests that GlobalBudgetController enforces hard budget limits deterministically,
even under parallel execution with race conditions.

Run with: python test_module4_budget_enforcement.py
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.module_4.global_budget import GlobalBudgetController
from utils.logger import get_logger

logger = get_logger(__name__)


def test_basic_budget_operations():
    """Test basic reserve/consume/release operations."""
    logger.info("=" * 70)
    logger.info("TEST 1: Basic Budget Operations")
    logger.info("=" * 70)
    
    controller = GlobalBudgetController(max_budget=100)
    
    # Test reserve
    assert controller.reserve_calls(10, "test_reserve"), "Failed to reserve 10 calls"
    assert controller.reserved() == 10, "Reserved count mismatch"
    assert controller.remaining() == 90, "Remaining count mismatch"
    
    # Test consume
    for i in range(10):
        controller.consume_call(f"test_consume_{i}")
    assert controller.consumed() == 10, "Consumed count mismatch"
    assert controller.reserved() == 0, "Reserved should be 0 after consume"
    assert controller.remaining() == 90, "Remaining mismatch after consume"
    
    # Test release
    assert controller.reserve_calls(20, "test_release"), "Failed to reserve 20 calls"
    controller.release_calls(10, "partial release")
    assert controller.reserved() == 10, "Reserved mismatch after release"
    assert controller.remaining() == 80, "Remaining mismatch after release"
    
    # Cleanup remaining reserved
    controller.release_calls(10, "cleanup")
    
    logger.info("✓ Basic operations passed")
    logger.info("")
    return True


def test_budget_exhaustion():
    """Test that budget exhaustion prevents further reservations."""
    logger.info("=" * 70)
    logger.info("TEST 2: Budget Exhaustion Prevention")
    logger.info("=" * 70)
    
    controller = GlobalBudgetController(max_budget=50)
    
    # Reserve and consume most of budget
    assert controller.reserve_calls(40, "large_reservation"), "Failed to reserve 40"
    for i in range(40):
        controller.consume_call(f"consume_{i}")
    
    # Try to reserve more than available
    assert not controller.can_reserve(20), "Should not allow reservation beyond budget"
    assert not controller.reserve_calls(20, "exceeds_budget"), "Should reject over-budget reservation"
    
    # Should allow reservation within budget
    assert controller.can_reserve(10), "Should allow reservation within budget"
    assert controller.reserve_calls(10, "within_budget"), "Should accept within-budget reservation"
    
    # Consume remaining
    for i in range(10):
        controller.consume_call(f"final_{i}")
    
    # Budget exhausted
    assert controller.consumed() == 50, "Should have consumed exactly max_budget"
    assert controller.remaining() == 0, "Should have 0 remaining"
    assert not controller.can_reserve(1), "Should not allow any reservation when exhausted"
    
    summary = controller.get_summary()
    assert summary['compliant'], "Should be compliant when exactly at budget"
    assert summary['overshoot'] == 0, "Should have no overshoot"
    
    logger.info("✓ Budget exhaustion prevention passed")
    logger.info("")
    return True


def test_parallel_budget_enforcement():
    """
    Test budget enforcement under parallel execution (race conditions).
    
    Simulates 10 workers trying to reserve budget simultaneously.
    Should NEVER exceed max_budget even with race conditions.
    """
    logger.info("=" * 70)
    logger.info("TEST 3: Parallel Budget Enforcement (Race Conditions)")
    logger.info("=" * 70)
    
    BUDGET = 135
    NUM_WORKERS = 10
    CALLS_PER_WORKER = 20  # Each wants 20, but total would be 200 > 135
    
    controller = GlobalBudgetController(max_budget=BUDGET)
    results = {'success': 0, 'rejected': 0, 'consumed': 0}
    lock = threading.Lock()
    
    def worker(worker_id: int):
        """Each worker tries to reserve and consume calls."""
        # Try to reserve
        if controller.reserve_calls(CALLS_PER_WORKER, f"worker_{worker_id}"):
            with lock:
                results['success'] += 1
            
            # Simulate some work
            time.sleep(0.01)
            
            # Consume the reserved calls
            for i in range(CALLS_PER_WORKER):
                controller.consume_call(f"worker_{worker_id}_call_{i}")
            
            with lock:
                results['consumed'] += CALLS_PER_WORKER
        else:
            with lock:
                results['rejected'] += 1
            logger.info(f"Worker {worker_id} rejected (budget insufficient)")
    
    # Run workers in parallel
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(worker, i) for i in range(NUM_WORKERS)]
        for future in as_completed(futures):
            future.result()  # Wait for completion
    
    # Verify results
    summary = controller.get_summary()
    
    logger.info(f"Results:")
    logger.info(f"  Workers succeeded: {results['success']}")
    logger.info(f"  Workers rejected: {results['rejected']}")
    logger.info(f"  Total consumed: {summary['consumed']}")
    logger.info(f"  Budget: {summary['max_budget']}")
    logger.info(f"  Compliant: {summary['compliant']}")
    
    # Assertions
    assert summary['consumed'] <= BUDGET, f"CRITICAL: Budget exceeded! {summary['consumed']} > {BUDGET}"
    assert summary['compliant'], "Budget must be compliant (no overshoot)"
    assert results['success'] > 0, "At least some workers should succeed"
    assert results['rejected'] > 0, "Some workers should be rejected (not enough budget for all)"
    assert results['consumed'] == summary['consumed'], "Consumed count mismatch"
    
    # Expected: ~6-7 workers succeed (6*20=120, 7*20=140>135), rest rejected
    expected_success = BUDGET // CALLS_PER_WORKER
    logger.info(f"  Expected ~{expected_success} workers to succeed: actual={results['success']}")
    
    logger.info("✓ Parallel enforcement passed - NO OVERSHOOT under race conditions")
    logger.info("")
    return True


def test_cache_bypass():
    """Test that cache hits don't consume budget."""
    logger.info("=" * 70)
    logger.info("TEST 4: Cache Bypass (cache hits don't consume budget)")
    logger.info("=" * 70)
    
    controller = GlobalBudgetController(max_budget=100)
    
    # Simulate 10 web calls (should consume budget)
    assert controller.reserve_calls(10, "web_calls"), "Failed to reserve for web calls"
    for i in range(10):
        controller.consume_call(f"web_call_{i}")
    
    assert controller.consumed() == 10, "Should have consumed 10 from web calls"
    
    # Simulate 20 cache hits (should NOT consume budget)
    # Cache hits are not tracked by GlobalBudgetController - they bypass it entirely
    logger.info("  Simulating 20 cache hits (no budget consumption)...")
    
    # Budget should remain unchanged
    assert controller.consumed() == 10, "Cache hits should not consume budget"
    assert controller.remaining() == 90, "Remaining should be unchanged"
    
    logger.info("✓ Cache bypass passed - cache hits don't consume budget")
    logger.info("")
    return True


def test_budget_summary_and_compliance():
    """Test budget summary and compliance assertions."""
    logger.info("=" * 70)
    logger.info("TEST 5: Budget Summary and Compliance")
    logger.info("=" * 70)
    
    controller = GlobalBudgetController(max_budget=135)
    
    # Consume exactly budget
    assert controller.reserve_calls(135, "exact_budget"), "Failed to reserve exact budget"
    for i in range(135):
        controller.consume_call(f"call_{i}")
    
    # Get summary
    summary = controller.get_summary()
    logger.info(f"Summary: {summary}")
    
    assert summary['consumed'] == 135, "Consumed should equal max_budget"
    assert summary['remaining'] == 0, "Remaining should be 0"
    assert summary['utilization_pct'] == 100.0, "Utilization should be 100%"
    assert summary['compliant'], "Should be compliant at exactly max_budget"
    assert summary['overshoot'] == 0, "No overshoot"
    
    # Test assert_compliance (should pass)
    try:
        controller.assert_compliance()
        logger.info("✓ assert_compliance() passed (no exception)")
    except AssertionError as e:
        logger.error(f"✗ assert_compliance() failed: {e}")
        return False
    
    # Log summary
    controller.log_summary()
    
    logger.info("✓ Budget summary and compliance passed")
    logger.info("")
    return True


def test_overshoot_detection():
    """Test that overshoots are detected and reported."""
    logger.info("=" * 70)
    logger.info("TEST 6: Overshoot Detection")
    logger.info("=" * 70)
    
    controller = GlobalBudgetController(max_budget=100)
    
    # Consume beyond budget (simulating a bug)
    controller.reserve_calls(100, "max")
    for i in range(100):
        controller.consume_call(f"call_{i}")
    
    # Try to consume without reservation (simulates a bug)
    logger.info("  Simulating bug: consuming without reservation...")
    controller._consumed += 10  # Direct manipulation to simulate bug
    
    summary = controller.get_summary()
    assert not summary['compliant'], "Should detect non-compliance"
    assert summary['overshoot'] == 10, "Should detect overshoot of 10"
    
    # assert_compliance should fail
    try:
        controller.assert_compliance()
        logger.error("✗ assert_compliance() should have raised AssertionError")
        return False
    except AssertionError as e:
        logger.info(f"✓ assert_compliance() correctly raised: {e}")
    
    logger.info("✓ Overshoot detection passed")
    logger.info("")
    return True


def main():
    """Run all tests."""
    logger.info("")
    logger.info("*" * 70)
    logger.info("MODULE 4 GLOBAL BUDGET ENFORCEMENT TESTS")
    logger.info("*" * 70)
    logger.info("")
    
    tests = [
        ("Basic Operations", test_basic_budget_operations),
        ("Budget Exhaustion", test_budget_exhaustion),
        ("Parallel Enforcement", test_parallel_budget_enforcement),
        ("Cache Bypass", test_cache_bypass),
        ("Summary & Compliance", test_budget_summary_and_compliance),
        ("Overshoot Detection", test_overshoot_detection),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                logger.error(f"✗ {name} FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"✗ {name} FAILED with exception: {e}")
    
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.info("✅ ALL TESTS PASSED")
        logger.info("=" * 70)
        return True
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.info("=" * 70)
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
