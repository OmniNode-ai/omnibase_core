"""
Concurrency tests for ONEX node components.

This package contains tests that validate thread safety guarantees and detect
race conditions in concurrent execution scenarios.

Test Categories:
- ModelComputeCache: Cache operations under concurrent load
- ThreadSafeComputeCache: Thread-safe wrapper validation
- NodeCompute: Parallel batch processing thread safety
- NodeReducer: FSM state thread safety and concurrent state transitions

See docs/guides/THREADING.md for complete thread safety documentation.
"""
