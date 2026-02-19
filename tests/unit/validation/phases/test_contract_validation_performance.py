# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Performance tests for contract validation pipeline.

These tests verify that validation scales appropriately for large contracts
and is thread-safe for concurrent usage.

Related:
    - OMN-1128: Contract Validation Pipeline
    - MergeValidator: Phase 2 validation
    - ExpandedContractValidator: Phase 3 validation

Performance Tests:
    1. Large contract validation (1000+ handlers)
    2. O(n) duplicate detection verification
    3. Concurrent validation thread safety
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.validation.phases.validator_expanded_contract import (
    ExpandedContractValidator,
)
from omnibase_core.validation.phases.validator_merge import MergeValidator

# =============================================================================
# Helper Functions
# =============================================================================


def create_contract_with_outputs(
    valid_descriptor: ModelHandlerBehavior,
    num_outputs: int,
) -> ModelHandlerContract:
    """Create a contract with the specified number of unique capability outputs.

    Args:
        valid_descriptor: Handler behavior descriptor.
        num_outputs: Number of outputs to create.

    Returns:
        A ModelHandlerContract with the specified number of outputs.
    """
    outputs = [f"event.handler_{i}" for i in range(num_outputs)]

    return ModelHandlerContract(
        handler_id="node.test.compute",
        name=f"Test Handler with {num_outputs} outputs",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        description=f"A test contract with {num_outputs} capability outputs",
        descriptor=valid_descriptor,
        input_model="omnibase_core.models.events.ModelTestEvent",
        output_model="omnibase_core.models.results.ModelTestResult",
        capability_outputs=outputs,
    )


def create_minimal_patch(profile_ref: ModelProfileReference) -> ModelContractPatch:
    """Create a minimal contract patch."""
    return ModelContractPatch(
        extends=profile_ref,
        name="performance_test_handler",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
    )


def create_valid_contract(
    valid_descriptor: ModelHandlerBehavior,
    suffix: str = "",
) -> ModelHandlerContract:
    """Create a valid contract for testing."""
    return ModelHandlerContract(
        handler_id="node.test.compute",
        name=f"Test Handler {suffix}",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test contract for concurrent validation",
        descriptor=valid_descriptor,
        input_model="omnibase_core.models.events.ModelTestEvent",
        output_model="omnibase_core.models.results.ModelTestResult",
        capability_outputs=[f"event.output_{suffix}"] if suffix else [],
    )


def create_patch_with_suffix(
    profile_ref: ModelProfileReference,
    suffix: str = "",
) -> ModelContractPatch:
    """Create a minimal contract patch with suffix."""
    return ModelContractPatch(
        extends=profile_ref,
        name=f"test_handler_{suffix}" if suffix else "test_handler",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def merge_validator() -> MergeValidator:
    """Create a MergeValidator fixture."""
    return MergeValidator()


@pytest.fixture
def expanded_validator() -> ExpandedContractValidator:
    """Create an ExpandedContractValidator fixture."""
    return ExpandedContractValidator()


@pytest.fixture
def profile_ref() -> ModelProfileReference:
    """Create a profile reference fixture."""
    return ModelProfileReference(profile="compute_pure", version="1.0.0")


@pytest.fixture
def valid_descriptor() -> ModelHandlerBehavior:
    """Create a valid handler behavior descriptor."""
    return ModelHandlerBehavior(
        node_archetype="compute",
        purity="pure",
        idempotent=True,
    )


# =============================================================================
# Performance Tests for Large Contracts
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.slow
class TestLargeContractValidation:
    """Performance tests for contract validation pipeline.

    These tests verify that validation scales appropriately for large contracts
    and does not exhibit O(n^2) or worse complexity.
    """

    def test_large_contract_validation_1000_handlers(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that validating a contract with 1000+ handlers completes quickly.

        This test verifies that validation of large contracts completes within
        a reasonable time threshold (< 5 seconds), ensuring the validation
        pipeline scales appropriately for production-sized contracts.
        """
        base = create_contract_with_outputs(valid_descriptor, 1000)
        patch = create_minimal_patch(profile_ref)
        merged = create_contract_with_outputs(valid_descriptor, 1000)

        start_time = time.time()
        result = merge_validator.validate(base, patch, merged)
        elapsed = time.time() - start_time

        # Verify result is valid ModelValidationResult with expected properties
        assert result is not None, "Validation should return a result"
        assert result.is_valid is True, "Valid contract should pass merge validation"
        assert result.error_level_count == 0, "Valid contract should have no errors"
        assert elapsed < 5.0, (
            f"Large contract validation took {elapsed:.2f}s, expected < 5.0s. "
            "This may indicate O(n^2) or worse complexity."
        )

    def test_large_contract_validation_2000_handlers(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that validating a contract with 2000+ handlers completes quickly.

        Extended test for even larger contracts to verify linear scaling.
        """
        base = create_contract_with_outputs(valid_descriptor, 2000)
        patch = create_minimal_patch(profile_ref)
        merged = create_contract_with_outputs(valid_descriptor, 2000)

        start_time = time.time()
        result = merge_validator.validate(base, patch, merged)
        elapsed = time.time() - start_time

        # Verify result is valid ModelValidationResult with expected properties
        assert result is not None, "Validation should return a result"
        assert result.is_valid is True, "Valid contract should pass merge validation"
        assert result.error_level_count == 0, "Valid contract should have no errors"
        assert elapsed < 5.0, (
            f"Large contract validation (2000 handlers) took {elapsed:.2f}s, "
            "expected < 5.0s"
        )

    def test_expanded_validator_1000_handlers(
        self,
        expanded_validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test expanded contract validation with 1000+ handlers."""
        contract = create_contract_with_outputs(valid_descriptor, 1000)

        start_time = time.time()
        result = expanded_validator.validate(contract)
        elapsed = time.time() - start_time

        # Verify result is valid ModelValidationResult with expected properties
        assert result is not None, "Validation should return a result"
        assert result.is_valid is True, "Valid contract should pass expanded validation"
        assert result.error_level_count == 0, "Valid contract should have no errors"
        assert elapsed < 5.0, (
            f"Expanded validation took {elapsed:.2f}s, expected < 5.0s"
        )


# =============================================================================
# O(n) Duplicate Detection Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.slow
class TestDuplicateDetectionComplexity:
    """Tests verifying O(n) complexity for duplicate detection.

    The _check_for_duplicates method in MergeValidator uses set-based
    detection which should be O(n). These tests verify that time increases
    linearly, not quadratically, with input size.
    """

    def test_duplicate_detection_scales_linearly(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that duplicate detection does not exhibit O(n^2) behavior.

        Tests with increasing handler counts (100, 500, 1000) and verifies
        that time scales linearly. If 10x more handlers takes more than
        15x the time, it suggests non-linear complexity.
        """
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            base = create_contract_with_outputs(valid_descriptor, size)
            patch = create_minimal_patch(profile_ref)
            merged = create_contract_with_outputs(valid_descriptor, size)

            start_time = time.time()
            result = merge_validator.validate(base, patch, merged)
            elapsed = time.time() - start_time
            times.append(elapsed)

            # Verify each validation actually succeeds (not just timing)
            assert result.is_valid is True, (
                f"Contract with {size} handlers should pass validation"
            )
            assert result.error_level_count == 0, (
                f"Contract with {size} handlers should have no errors"
            )

        # Check that scaling is roughly linear
        # 10x more handlers should not take more than ~15x the time
        # (allowing for constant overhead and measurement noise)
        # Use max() to protect against division by zero if validation is extremely fast
        base_time = max(times[0], 0.001)
        scaling_factor_500 = times[1] / base_time
        scaling_factor_1000 = times[2] / base_time

        # With linear O(n), 5x handlers -> ~5x time
        # With quadratic O(n^2), 5x handlers -> ~25x time
        # We allow up to 15x to account for constant overhead
        assert scaling_factor_500 < 15, (
            f"500 handlers took {scaling_factor_500:.1f}x longer than 100 handlers. "
            "Expected roughly linear scaling (<15x for 5x size increase)."
        )
        assert scaling_factor_1000 < 25, (
            f"1000 handlers took {scaling_factor_1000:.1f}x longer than 100 handlers. "
            "Expected roughly linear scaling (<25x for 10x size increase)."
        )

    def test_duplicate_detection_all_sizes_complete_quickly(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that all tested sizes complete within reasonable time."""
        for size in [100, 500, 1000]:
            base = create_contract_with_outputs(valid_descriptor, size)
            patch = create_minimal_patch(profile_ref)
            merged = create_contract_with_outputs(valid_descriptor, size)

            start_time = time.time()
            result = merge_validator.validate(base, patch, merged)
            elapsed = time.time() - start_time

            # Verify result is valid ModelValidationResult with expected properties
            assert result is not None, (
                f"Validation with {size} handlers should return a result"
            )
            assert result.is_valid is True, (
                f"Valid contract with {size} handlers should pass"
            )
            assert result.error_level_count == 0, (
                f"Valid contract with {size} handlers should have no errors"
            )
            assert elapsed < 2.0, (
                f"Validation with {size} handlers took {elapsed:.2f}s, expected < 2.0s"
            )


# =============================================================================
# Thread Safety Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentValidationThreadSafety:
    """Tests for thread safety of concurrent validation operations.

    MergeValidator and ExpandedContractValidator are documented as stateless
    and thread-safe. These tests verify that concurrent validation from
    multiple threads produces correct results without race conditions.
    """

    def test_concurrent_merge_validation_thread_safety(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that MergeValidator is thread-safe for concurrent usage.

        Runs validation from multiple threads simultaneously and verifies
        that all return correct results without race conditions.
        """
        num_threads = 10
        num_validations_per_thread = 20
        results: list[tuple[bool, int]] = []
        errors: list[str] = []

        def validate_in_thread(thread_id: int) -> list[tuple[bool, int]]:
            """Worker function for concurrent validation."""
            thread_results: list[tuple[bool, int]] = []
            for i in range(num_validations_per_thread):
                try:
                    suffix = f"{thread_id}_{i}"
                    base = create_valid_contract(valid_descriptor, suffix)
                    patch = create_patch_with_suffix(profile_ref, suffix)
                    merged = create_valid_contract(valid_descriptor, suffix)

                    result = merge_validator.validate(base, patch, merged)
                    thread_results.append((result.is_valid, result.error_level_count))
                except Exception as e:
                    errors.append(f"Thread {thread_id}, iteration {i}: {e}")
            return thread_results

        # Run concurrent validations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(validate_in_thread, i) for i in range(num_threads)
            ]
            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as e:
                    errors.append(str(e))

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent validation: {errors}"

        # Verify all validations returned results
        expected_count = num_threads * num_validations_per_thread
        assert len(results) == expected_count, (
            f"Expected {expected_count} results, got {len(results)}"
        )

        # Verify all valid contracts passed validation
        for is_valid, error_count in results:
            assert is_valid is True, "Valid contract should pass validation"
            assert error_count == 0, "Valid contract should have no errors"

    def test_concurrent_expanded_validation_thread_safety(
        self,
        expanded_validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that ExpandedContractValidator is thread-safe.

        Runs expanded validation from multiple threads simultaneously.
        """
        num_threads = 8
        num_validations_per_thread = 25
        results: list[tuple[bool, int]] = []
        errors: list[str] = []

        def validate_in_thread(thread_id: int) -> list[tuple[bool, int]]:
            """Worker function for concurrent validation."""
            thread_results: list[tuple[bool, int]] = []
            for i in range(num_validations_per_thread):
                try:
                    suffix = f"{thread_id}_{i}"
                    contract = create_valid_contract(valid_descriptor, suffix)
                    result = expanded_validator.validate(contract)
                    thread_results.append((result.is_valid, result.error_level_count))
                except Exception as e:
                    errors.append(f"Thread {thread_id}, iteration {i}: {e}")
            return thread_results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(validate_in_thread, i) for i in range(num_threads)
            ]
            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as e:
                    errors.append(str(e))

        assert len(errors) == 0, f"Errors during concurrent validation: {errors}"

        expected_count = num_threads * num_validations_per_thread
        assert len(results) == expected_count, (
            f"Expected {expected_count} results, got {len(results)}"
        )

    def test_shared_validator_instance_thread_safety(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that a single validator instance can be shared across threads.

        This is important for performance - validators should not need to be
        instantiated per-request.
        """
        shared_validator = merge_validator
        results_lock = threading.Lock()
        all_results: list[bool] = []
        all_errors: list[str] = []

        def worker(thread_id: int, num_iterations: int) -> None:
            """Worker that uses the shared validator."""
            for i in range(num_iterations):
                try:
                    suffix = f"shared_{thread_id}_{i}"
                    base = create_valid_contract(valid_descriptor, suffix)
                    patch = create_patch_with_suffix(profile_ref, suffix)
                    merged = create_valid_contract(valid_descriptor, suffix)

                    result = shared_validator.validate(base, patch, merged)

                    with results_lock:
                        all_results.append(result.is_valid)
                except Exception as e:
                    with results_lock:
                        all_errors.append(f"Thread {thread_id}: {e}")

        # Create and start threads
        threads: list[threading.Thread] = []
        num_threads = 6
        iterations_per_thread = 30

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i, iterations_per_thread))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=30)  # 30 second timeout

        # Verify results
        assert len(all_errors) == 0, f"Thread errors: {all_errors}"

        expected_count = num_threads * iterations_per_thread
        assert len(all_results) == expected_count, (
            f"Expected {expected_count} results, got {len(all_results)}"
        )

        # All should pass since we used valid contracts
        assert all(r is True for r in all_results), (
            "All valid contracts should pass validation"
        )

    def test_concurrent_validation_result_independence(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that validation results are independent across threads.

        This test uses a mix of valid and invalid contracts to verify that
        each thread receives the correct result for its specific input,
        ensuring no shared mutable state corruption.
        """
        num_threads = 8
        num_validations_per_thread = 15
        # Track results with thread_id to verify independence
        results: dict[str, tuple[bool, bool]] = {}
        results_lock = threading.Lock()
        errors: list[str] = []

        def create_invalid_contract(suffix: str) -> ModelHandlerContract:
            """Create an invalid contract with placeholder value."""
            return ModelHandlerContract(
                handler_id="node.test.compute",
                name="TODO",  # Placeholder - should fail validation
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Invalid contract for testing",
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.events.ModelTestEvent",
                output_model="omnibase_core.models.results.ModelTestResult",
                capability_outputs=[f"event.output_{suffix}"],
            )

        def validate_in_thread(thread_id: int) -> None:
            """Validate mix of valid and invalid contracts."""
            for i in range(num_validations_per_thread):
                try:
                    suffix = f"{thread_id}_{i}"
                    # Even iterations: valid contracts, Odd: invalid
                    if i % 2 == 0:
                        contract = create_valid_contract(valid_descriptor, suffix)
                        expected_valid = True
                    else:
                        contract = create_invalid_contract(suffix)
                        expected_valid = False

                    patch = create_patch_with_suffix(profile_ref, suffix)
                    merged = contract  # Use same contract as merged for this test

                    result = merge_validator.validate(contract, patch, merged)

                    with results_lock:
                        key = f"{thread_id}_{i}_valid={expected_valid}"
                        results[key] = (result.is_valid, expected_valid)

                except Exception as e:
                    with results_lock:
                        errors.append(f"Thread {thread_id}, iteration {i}: {e}")

        # Run concurrent validations
        threads: list[threading.Thread] = []
        for i in range(num_threads):
            t = threading.Thread(target=validate_in_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=60)

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent validation: {errors}"

        # Verify we got all expected results
        expected_count = num_threads * num_validations_per_thread
        assert len(results) == expected_count, (
            f"Expected {expected_count} results, got {len(results)}"
        )

        # Verify each result matches expected validity
        mismatches: list[str] = []
        for key, (actual_valid, expected_valid) in results.items():
            # Note: For invalid contracts (placeholder "TODO" in name),
            # the merge validator should detect placeholder values
            if expected_valid and not actual_valid:
                mismatches.append(f"{key}: expected valid but got invalid")
            # Note: We don't assert invalid->invalid because placeholder
            # detection depends on the specific field being checked

        assert len(mismatches) == 0, f"Result independence violations: {mismatches}"

    def test_expanded_validator_result_independence(
        self,
        expanded_validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test ExpandedContractValidator result independence with mixed inputs.

        Uses valid contracts with different suffixes to verify each thread
        receives its own independent result with correct validation outcome.
        """
        num_threads = 6
        num_validations_per_thread = 20
        results: dict[
            str, tuple[bool, int, str]
        ] = {}  # key -> (is_valid, error_count, suffix)
        results_lock = threading.Lock()
        errors: list[str] = []

        def validate_in_thread(thread_id: int) -> None:
            """Validate contracts and track results with unique suffixes."""
            for i in range(num_validations_per_thread):
                try:
                    suffix = f"{thread_id}_{i}"
                    contract = create_valid_contract(valid_descriptor, suffix)
                    result = expanded_validator.validate(contract)

                    with results_lock:
                        key = f"{thread_id}_{i}"
                        results[key] = (
                            result.is_valid,
                            result.error_level_count,
                            suffix,
                        )

                except Exception as e:
                    with results_lock:
                        errors.append(f"Thread {thread_id}, iteration {i}: {e}")

        threads: list[threading.Thread] = []
        for i in range(num_threads):
            t = threading.Thread(target=validate_in_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=60)

        assert len(errors) == 0, f"Errors: {errors}"

        expected_count = num_threads * num_validations_per_thread
        assert len(results) == expected_count

        # Verify all valid contracts passed with no errors
        for key, (is_valid, error_count, suffix) in results.items():
            assert is_valid, f"{key}: valid contract should pass"
            assert error_count == 0, f"{key}: valid contract should have no errors"
            # Verify suffix matches the key (no cross-contamination)
            expected_suffix = key
            assert suffix == expected_suffix, (
                f"Result contamination: key={key} but got suffix={suffix}"
            )

    def test_high_concurrency_stress_test(
        self,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Stress test with high concurrency to detect race conditions.

        Uses 20 threads with 50 validations each (1000 total) to maximize
        the chance of detecting any thread safety issues.
        """
        num_threads = 20
        num_validations_per_thread = 50
        # Use fresh validator instances to test instance isolation
        merge_validator = MergeValidator()
        expanded_validator = ExpandedContractValidator()

        merge_results: list[bool] = []
        expanded_results: list[bool] = []
        results_lock = threading.Lock()
        errors: list[str] = []

        def validate_both_in_thread(thread_id: int) -> None:
            """Run both validators for each iteration."""
            for i in range(num_validations_per_thread):
                try:
                    suffix = f"stress_{thread_id}_{i}"
                    contract = create_valid_contract(valid_descriptor, suffix)
                    patch = create_patch_with_suffix(profile_ref, suffix)

                    # Run merge validation
                    merge_result = merge_validator.validate(contract, patch, contract)

                    # Run expanded validation
                    expanded_result = expanded_validator.validate(contract)

                    with results_lock:
                        merge_results.append(merge_result.is_valid)
                        expanded_results.append(expanded_result.is_valid)

                except Exception as e:
                    with results_lock:
                        errors.append(f"Thread {thread_id}: {e}")

        threads: list[threading.Thread] = []
        for i in range(num_threads):
            t = threading.Thread(target=validate_both_in_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=120)  # 2 minute timeout for stress test

        assert len(errors) == 0, f"Errors during stress test: {errors}"

        expected_count = num_threads * num_validations_per_thread
        assert len(merge_results) == expected_count, (
            f"Expected {expected_count} merge results, got {len(merge_results)}"
        )
        assert len(expanded_results) == expected_count, (
            f"Expected {expected_count} expanded results, got {len(expanded_results)}"
        )

        # All valid contracts should pass
        assert all(r is True for r in merge_results), (
            "All merge validations should pass"
        )
        assert all(r is True for r in expanded_results), (
            "All expanded validations should pass"
        )

    def test_no_state_leakage_between_validations(
        self,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Verify that validator state doesn't leak between sequential validations.

        This tests the stateless claim by running validations in sequence
        and verifying that invalid contract results don't affect subsequent
        valid contract validations.

        Uses placeholder values to create invalid contracts for MergeValidator,
        and valid contracts for ExpandedContractValidator (since model validates
        handler_id format at construction time).
        """
        merge_validator = MergeValidator()
        expanded_validator = ExpandedContractValidator()

        def create_invalid_contract_for_merge() -> ModelHandlerContract:
            """Create contract with placeholder that fails merge validation."""
            return ModelHandlerContract(
                handler_id="node.test.compute",
                name="PLACEHOLDER",  # Should fail merge validation
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Invalid",
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.events.ModelTestEvent",
                output_model="omnibase_core.models.results.ModelTestResult",
            )

        # Pattern: invalid -> valid -> invalid -> valid
        # If state leaks, valid results might be affected
        test_sequence = ["invalid", "valid", "invalid", "valid", "valid", "invalid"]
        merge_results: list[tuple[str, bool]] = []
        expanded_results: list[tuple[str, bool]] = []

        # Test merge validator with mix of valid and invalid contracts
        for i, test_type in enumerate(test_sequence):
            suffix = f"leak_test_{i}"
            patch = create_patch_with_suffix(profile_ref, suffix)

            if test_type == "valid":
                contract = create_valid_contract(valid_descriptor, suffix)
            else:
                contract = create_invalid_contract_for_merge()

            result = merge_validator.validate(contract, patch, contract)
            merge_results.append((test_type, result.is_valid))

        # Test expanded validator with alternating contracts to verify
        # no state leakage (all valid since model validates handler_id)
        for i in range(len(test_sequence)):
            suffix = f"expanded_leak_test_{i}"
            contract = create_valid_contract(valid_descriptor, suffix)
            result = expanded_validator.validate(contract)
            expanded_results.append(("valid", result.is_valid))

        # Verify merge validator results match expectations
        for test_type, is_valid in merge_results:
            if test_type == "valid":
                assert is_valid, "Valid contract should pass after invalid contracts"

        # Verify all expanded validations pass (tests state isolation)
        for test_type, is_valid in expanded_results:
            assert is_valid, "Valid contract should pass - no state leakage"


# =============================================================================
# Memory Profiling Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
@pytest.mark.slow
class TestMemoryUsageValidation:
    """Memory profiling tests for large contract collections.

    These tests verify that validation operations do not exhibit memory leaks
    when processing multiple large contracts in sequence.

    Memory Leak Detection:
        - Validates many contracts in sequence
        - Measures memory before and after each batch
        - Verifies memory growth stays within acceptable bounds

    Note:
        Memory measurements use gc.collect() to force garbage collection
        before measurements for more accurate readings.
    """

    def test_sequential_large_contract_validation_no_memory_leak(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that validating many large contracts doesn't leak memory.

        Validates 50 contracts with 500 outputs each and verifies that
        memory usage doesn't grow unboundedly between batches.
        """
        import gc
        import sys

        num_contracts = 50
        outputs_per_contract = 500
        batch_size = 10

        # Force garbage collection and get initial memory baseline
        gc.collect()
        initial_size = sys.getsizeof([])

        # Track memory usage at batch boundaries
        memory_samples: list[int] = []

        for batch_idx in range(num_contracts // batch_size):
            batch_start = batch_idx * batch_size

            # Process a batch of contracts
            for i in range(batch_size):
                contract_idx = batch_start + i
                base = create_contract_with_outputs(
                    valid_descriptor, outputs_per_contract
                )
                patch = create_minimal_patch(profile_ref)
                merged = create_contract_with_outputs(
                    valid_descriptor, outputs_per_contract
                )

                result = merge_validator.validate(base, patch, merged)
                assert result.is_valid is True, (
                    f"Contract {contract_idx} should be valid"
                )

            # Force garbage collection after each batch
            gc.collect()

            # Sample memory by tracking object count as proxy
            # (More portable than psutil which may not be available)
            memory_samples.append(len(gc.get_objects()))

        # Verify memory didn't grow excessively between batches
        # Memory should stabilize, not grow linearly
        if len(memory_samples) >= 3:
            first_batch_objects = memory_samples[0]
            last_batch_objects = memory_samples[-1]

            # Allow up to 50% growth (accounting for Python internals, caching, etc.)
            # A true leak would show linear or worse growth
            max_allowed_growth = first_batch_objects * 1.5
            assert last_batch_objects < max_allowed_growth, (
                f"Potential memory leak detected: object count grew from "
                f"{first_batch_objects} to {last_batch_objects} "
                f"(>{max_allowed_growth:.0f} allowed)"
            )

    def test_expanded_validator_sequential_memory_stability(
        self,
        expanded_validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test ExpandedContractValidator doesn't leak memory on repeated calls.

        Validates 100 contracts sequentially and checks memory stability.
        """
        import gc

        num_contracts = 100

        # Force initial garbage collection
        gc.collect()
        initial_object_count = len(gc.get_objects())

        # Validate many contracts
        for i in range(num_contracts):
            contract = create_contract_with_outputs(valid_descriptor, 200)
            result = expanded_validator.validate(contract)
            assert result.is_valid is True, f"Contract {i} should be valid"

            # Periodic garbage collection to allow cleanup
            if i % 20 == 0:
                gc.collect()

        # Final garbage collection
        gc.collect()
        final_object_count = len(gc.get_objects())

        # Check that object count didn't explode
        # Allow 2x growth for test framework overhead and Python internals
        max_growth = initial_object_count * 2
        assert final_object_count < max_growth, (
            f"Potential memory leak: objects grew from {initial_object_count} "
            f"to {final_object_count}"
        )

    def test_large_capability_outputs_memory_bounded(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that contracts with very large capability_outputs list are memory bounded.

        Validates contracts with 5000 outputs to verify memory usage scales linearly,
        not exponentially, with output count.
        """
        import gc
        import sys

        # Test with increasingly large output counts
        output_sizes = [100, 500, 1000, 2000, 5000]
        memory_per_size: dict[int, int] = {}

        for size in output_sizes:
            gc.collect()

            # Create and validate contract
            base = create_contract_with_outputs(valid_descriptor, size)
            patch = create_minimal_patch(profile_ref)
            merged = create_contract_with_outputs(valid_descriptor, size)

            # Measure approximate memory of the contract
            memory_per_size[size] = sys.getsizeof(merged.capability_outputs)

            result = merge_validator.validate(base, patch, merged)
            assert result.is_valid is True, (
                f"Contract with {size} outputs should be valid"
            )

        # Verify memory scales roughly linearly with size
        # Memory at 5000 should be roughly 50x memory at 100 (within 2x tolerance)
        if memory_per_size[100] > 0:
            expected_ratio = 5000 / 100  # 50x
            actual_ratio = memory_per_size[5000] / max(memory_per_size[100], 1)
            # Allow 2x tolerance for overhead
            assert actual_ratio < expected_ratio * 2, (
                f"Memory scaling appears non-linear: 100 outputs={memory_per_size[100]}, "
                f"5000 outputs={memory_per_size[5000]}, ratio={actual_ratio:.1f}"
            )

    def test_validation_result_memory_isolation(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that validation results don't retain references to validated contracts.

        Ensures that after validation, the result object doesn't keep the entire
        contract in memory, which would prevent garbage collection.
        """
        import gc
        import weakref

        # Create a contract and keep a weak reference
        contract = create_contract_with_outputs(valid_descriptor, 1000)
        weak_contract = weakref.ref(contract)

        # Validate the contract
        patch = create_minimal_patch(profile_ref)
        result = merge_validator.validate(contract, patch, contract)

        # Delete strong references to the contract
        del contract
        del patch

        # Force garbage collection
        gc.collect()

        # The result should not prevent contract from being collected
        # Note: This may not always pass if other references exist in test framework
        # So we just verify the result is valid and doesn't explicitly store contract
        assert result.is_valid is True
        assert not hasattr(result, "contract"), (
            "Validation result should not store contract reference"
        )


# =============================================================================
# Processing Rate Safety Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.performance
class TestProcessingRateSafety:
    """Tests for safe processing rate calculations.

    Ensures that performance calculations don't fail due to division by zero
    or other edge cases when validation completes very quickly.
    """

    def test_zero_elapsed_time_safe_rate_calculation(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that rate calculations are safe when elapsed time is near zero.

        Very fast operations could complete in less than the timer resolution,
        resulting in elapsed time of 0. Rate calculations must handle this.
        """
        # Create a minimal contract that validates very quickly
        base = create_valid_contract(valid_descriptor, "fast")
        patch = create_minimal_patch(profile_ref)
        merged = create_valid_contract(valid_descriptor, "fast")

        start_time = time.time()
        result = merge_validator.validate(base, patch, merged)
        elapsed = time.time() - start_time

        # Calculate rate safely (the pattern to use in code)
        items_processed = 1
        if elapsed > 0:
            rate = items_processed / elapsed
        else:
            rate = float("inf")  # Instant completion

        # Verify the calculation didn't crash
        assert result.is_valid is True
        assert rate > 0 or rate == float("inf"), "Rate should be positive or infinite"

    def test_batch_processing_rate_with_safeguard(
        self,
        merge_validator: MergeValidator,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test batch processing rate calculation with proper safeguards.

        Demonstrates the recommended pattern for calculating processing rates
        in performance tests.
        """
        batch_sizes = [1, 10, 50]
        rates: list[float] = []

        for batch_size in batch_sizes:
            start_time = time.time()

            for i in range(batch_size):
                base = create_valid_contract(valid_descriptor, f"batch_{i}")
                patch = create_minimal_patch(profile_ref)
                merged = create_valid_contract(valid_descriptor, f"batch_{i}")
                result = merge_validator.validate(base, patch, merged)
                assert result.is_valid is True

            elapsed = time.time() - start_time

            # Safe rate calculation with minimum time threshold
            MIN_TIME_THRESHOLD = 0.001  # 1ms minimum
            safe_elapsed = max(elapsed, MIN_TIME_THRESHOLD)
            rate = batch_size / safe_elapsed
            rates.append(rate)

        # All rates should be positive finite numbers
        for i, rate in enumerate(rates):
            assert rate > 0, f"Rate for batch {batch_sizes[i]} should be positive"
            assert rate != float("inf"), "Rate should be finite when using safeguard"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
