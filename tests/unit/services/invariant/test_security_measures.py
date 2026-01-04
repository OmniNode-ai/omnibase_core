# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Tests for security measures in the invariant evaluator service.

This module tests security protections including:
- Allow-list prefix boundary matching (prevents prefix bypass attacks)
- ReDoS protection for regex operations
- Field path depth limits to prevent DoS
"""

import pytest

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestAllowListBoundaryMatching:
    """Tests for allow-list prefix boundary matching security.

    These tests verify that prefix matching uses proper boundaries to prevent
    attacks where a malicious module like "numpy_malicious" could match an
    allow-list entry for "numpy".
    """

    def test_prefix_blocks_similar_module_names(self) -> None:
        """Verify that 'numpy_malicious' does not match allow-list entry 'numpy'.

        This is the critical security test for prefix boundary matching.
        """
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["numpy"])

        # "numpy_malicious" should NOT match "numpy" allow-list entry
        assert evaluator._is_import_path_allowed("numpy_malicious") is False
        assert evaluator._is_import_path_allowed("numpy_malicious.evil_func") is False
        assert evaluator._is_import_path_allowed("numpy_extended") is False
        assert evaluator._is_import_path_allowed("numpy_evil:hack") is False

    def test_prefix_allows_exact_match(self) -> None:
        """Verify exact module match is allowed."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["numpy"])

        assert evaluator._is_import_path_allowed("numpy") is True

    def test_prefix_allows_submodule_with_dot(self) -> None:
        """Verify submodule with dot separator is allowed."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["numpy"])

        assert evaluator._is_import_path_allowed("numpy.array") is True
        assert evaluator._is_import_path_allowed("numpy.linalg.solve") is True

    def test_prefix_allows_function_with_colon(self) -> None:
        """Verify function with colon separator is allowed."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["numpy"])

        assert evaluator._is_import_path_allowed("numpy:array") is True

    def test_prefix_blocks_completely_different_modules(self) -> None:
        """Verify completely different modules are blocked."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["numpy"])

        assert evaluator._is_import_path_allowed("os.system") is False
        assert evaluator._is_import_path_allowed("builtins.eval") is False

    def test_module_path_blocks_similar_module_names(self) -> None:
        """Verify _is_module_path_allowed also uses boundary matching."""
        evaluator = ServiceInvariantEvaluator(
            allowed_import_paths=["tests.unit.services"]
        )

        # Should block similar-looking but different module paths
        assert evaluator._is_module_path_allowed("tests.unit.services_evil") is False
        assert (
            evaluator._is_module_path_allowed("tests.unit.services_malicious") is False
        )

        # Should allow exact match and proper submodules
        assert evaluator._is_module_path_allowed("tests.unit.services") is True
        assert (
            evaluator._is_module_path_allowed("tests.unit.services.invariant") is True
        )

    def test_empty_prefix_is_ignored(self) -> None:
        """Verify empty strings in allow-list are ignored for security."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["", "safe.module"])

        # Empty prefix should not match anything
        assert evaluator._is_import_path_allowed("anything") is False
        assert evaluator._is_import_path_allowed("safe.module.func") is True

    def test_invalid_prefix_format_is_ignored(self) -> None:
        """Verify malformed prefixes in allow-list are ignored."""
        evaluator = ServiceInvariantEvaluator(
            allowed_import_paths=["123invalid", "valid.module", "spaces not allowed"]
        )

        # Invalid prefixes should be skipped, valid one should work
        assert evaluator._is_import_path_allowed("123invalid.func") is False
        assert evaluator._is_import_path_allowed("valid.module.func") is True

    def test_callable_path_format_validation(self) -> None:
        """Verify that malformed callable paths are rejected."""
        evaluator = ServiceInvariantEvaluator(allowed_import_paths=["anything"])

        # Invalid path formats should be rejected before allow-list check
        assert evaluator._is_import_path_allowed("") is False
        assert evaluator._is_import_path_allowed("123.invalid") is False
        assert evaluator._is_import_path_allowed("has spaces.module") is False
        assert evaluator._is_import_path_allowed("special!chars.module") is False


@pytest.mark.unit
class TestReDoSProtection:
    """Tests for ReDoS (Regular Expression Denial of Service) protection."""

    def test_dangerous_nested_quantifiers_rejected(self) -> None:
        """Verify patterns with nested quantifiers are rejected."""
        evaluator = ServiceInvariantEvaluator()

        # Nested quantifiers like (a+)+ cause catastrophic backtracking
        is_safe, error_msg = evaluator._is_regex_safe(r"(a+)+")
        assert is_safe is False
        assert "nested quantifiers" in error_msg.lower()

    def test_dangerous_overlapping_alternation_rejected(self) -> None:
        """Verify patterns with alternation and quantifiers are rejected."""
        evaluator = ServiceInvariantEvaluator()

        # Alternation with outer quantifier: (a|b)+
        is_safe, _error_msg = evaluator._is_regex_safe(r"(a|b)+")
        assert is_safe is False

    def test_dangerous_multiple_wildcards_rejected(self) -> None:
        """Verify patterns with multiple .* sequences are rejected."""
        evaluator = ServiceInvariantEvaluator()

        # Multiple .* can cause exponential backtracking
        is_safe, _error_msg = evaluator._is_regex_safe(r".*.*.*")
        assert is_safe is False

    def test_pattern_length_limit_enforced(self) -> None:
        """Verify overly long patterns are rejected."""
        evaluator = ServiceInvariantEvaluator()

        # Create pattern longer than MAX_REGEX_PATTERN_LENGTH
        long_pattern = "a" * (evaluator.MAX_REGEX_PATTERN_LENGTH + 1)
        is_safe, error_msg = evaluator._is_regex_safe(long_pattern)
        assert is_safe is False
        assert "too long" in error_msg.lower()

    def test_safe_patterns_accepted(self) -> None:
        """Verify safe regex patterns are accepted."""
        evaluator = ServiceInvariantEvaluator()

        safe_patterns = [
            r"^\d+$",
            r"[a-z]+",
            r"hello world",
            r"^prefix.*suffix$",
            r"\w+@\w+\.\w+",
        ]

        for pattern in safe_patterns:
            is_safe, error_msg = evaluator._is_regex_safe(pattern)
            assert is_safe is True, f"Pattern {pattern!r} should be safe: {error_msg}"

    def test_invalid_regex_syntax_rejected(self) -> None:
        """Verify patterns with invalid syntax are rejected."""
        evaluator = ServiceInvariantEvaluator()

        is_safe, error_msg = evaluator._is_regex_safe(r"[invalid")
        assert is_safe is False
        assert "invalid regex pattern" in error_msg.lower()

    def test_safe_regex_search_with_dangerous_pattern(self) -> None:
        """Verify safe_regex_search rejects dangerous patterns."""
        evaluator = ServiceInvariantEvaluator()

        success, match, error_msg = evaluator._safe_regex_search(r"(a+)+", "aaaaaa")
        assert success is False
        assert match is None
        assert "nested quantifiers" in error_msg.lower()

    def test_safe_regex_search_input_length_limit(self) -> None:
        """Verify input text length is limited."""
        evaluator = ServiceInvariantEvaluator()

        # Create input longer than MAX_REGEX_INPUT_LENGTH
        long_input = "a" * (evaluator.MAX_REGEX_INPUT_LENGTH + 1)
        success, _match, error_msg = evaluator._safe_regex_search(r"\d+", long_input)
        assert success is False
        assert "too long" in error_msg.lower()

    def test_safe_regex_search_returns_match(self) -> None:
        """Verify safe_regex_search returns matches correctly."""
        evaluator = ServiceInvariantEvaluator()

        success, match, error_msg = evaluator._safe_regex_search(r"\d+", "abc123def")
        assert success is True
        assert match is not None
        assert match.group() == "123"
        assert error_msg == ""

    def test_safe_regex_search_returns_none_for_no_match(self) -> None:
        """Verify safe_regex_search returns None when no match found."""
        evaluator = ServiceInvariantEvaluator()

        success, match, error_msg = evaluator._safe_regex_search(r"\d+", "no numbers")
        assert success is True
        assert match is None
        assert error_msg == ""


@pytest.mark.unit
class TestFieldPathDepthLimit:
    """Tests for field path depth limit to prevent DoS attacks."""

    def test_shallow_path_allowed(self) -> None:
        """Verify paths within depth limit are resolved."""
        evaluator = ServiceInvariantEvaluator()

        data = {"level1": {"level2": {"level3": "value"}}}
        found, value = evaluator._resolve_field_path(data, "level1.level2.level3")

        assert found is True
        assert value == "value"

    def test_max_depth_allowed(self) -> None:
        """Verify paths at exactly max depth are allowed."""
        evaluator = ServiceInvariantEvaluator()

        # Build nested data structure with exactly MAX_FIELD_PATH_DEPTH levels
        # Path will have MAX_FIELD_PATH_DEPTH segments: level0.level1...level(N-2).value
        # Total segments = MAX_FIELD_PATH_DEPTH

        # Start with the innermost value
        data: dict[str, object] = {"value": "found"}

        # Build up the nesting (MAX_FIELD_PATH_DEPTH - 1 levels before "value")
        for i in range(evaluator.MAX_FIELD_PATH_DEPTH - 1, 0, -1):
            data = {f"level{i - 1}": data}

        # Build path with exactly MAX_FIELD_PATH_DEPTH segments
        path_parts = [f"level{i}" for i in range(evaluator.MAX_FIELD_PATH_DEPTH - 1)]
        path_parts.append("value")
        path = ".".join(path_parts)

        # Verify we have exactly max depth
        assert len(path.split(".")) == evaluator.MAX_FIELD_PATH_DEPTH

        found, value = evaluator._resolve_field_path(data, path)
        assert found is True
        assert value == "found"

    def test_exceeds_depth_limit_blocked(self) -> None:
        """Verify paths exceeding depth limit are blocked."""
        evaluator = ServiceInvariantEvaluator()

        # Create path with more parts than MAX_FIELD_PATH_DEPTH
        path_parts = [f"level{i}" for i in range(evaluator.MAX_FIELD_PATH_DEPTH + 1)]
        deep_path = ".".join(path_parts)

        # Even with matching data, should be blocked
        found, value = evaluator._resolve_field_path({}, deep_path)
        assert found is False
        assert value is None

    def test_depth_limit_value_is_reasonable(self) -> None:
        """Verify MAX_FIELD_PATH_DEPTH is set to a reasonable value."""
        evaluator = ServiceInvariantEvaluator()

        # Should be between 10-30 for reasonable use cases
        assert 10 <= evaluator.MAX_FIELD_PATH_DEPTH <= 30

    def test_field_presence_respects_depth_limit(self) -> None:
        """Verify FIELD_PRESENCE evaluation respects depth limit."""
        evaluator = ServiceInvariantEvaluator()

        # Create path exceeding depth limit
        path_parts = [f"level{i}" for i in range(evaluator.MAX_FIELD_PATH_DEPTH + 5)]
        deep_path = ".".join(path_parts)

        invariant = ModelInvariant(
            name="Deep Field Check",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumInvariantSeverity.WARNING,
            config={"fields": [deep_path]},
        )

        result = evaluator.evaluate(invariant, {"any": "data"})

        # Should fail due to depth limit, not just missing field
        assert result.passed is False


@pytest.mark.unit
class TestSecurityIntegration:
    """Integration tests for security measures working together."""

    def test_custom_callable_security_chain(self) -> None:
        """Verify the full security chain for custom callables."""
        evaluator = ServiceInvariantEvaluator(
            allowed_import_paths=["tests.unit.services.invariant"]
        )

        # Attempt to use a malicious-looking callable path
        invariant = ModelInvariant(
            name="Security Test",
            type=EnumInvariantType.CUSTOM,
            severity=EnumInvariantSeverity.CRITICAL,
            config={
                "callable_path": "tests.unit.services.invariant_malicious.evil_func"
            },
        )

        result = evaluator.evaluate(invariant, {"any": "data"})

        # Should be blocked by allow-list boundary matching
        assert result.passed is False
        assert "allow" in result.message.lower() or "not in" in result.message.lower()

    def test_field_value_pattern_with_redos_protection(self) -> None:
        """Verify FIELD_VALUE evaluation has ReDoS protection."""
        evaluator = ServiceInvariantEvaluator()

        # Attempt to use a dangerous regex pattern
        invariant = ModelInvariant(
            name="ReDoS Test",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumInvariantSeverity.WARNING,
            config={
                "field_path": "test_field",
                "pattern": r"(a+)+$",  # Dangerous nested quantifier
            },
        )

        result = evaluator.evaluate(invariant, {"test_field": "aaaaaaaaaaaa"})

        # Should fail due to dangerous pattern detection
        assert result.passed is False
        assert "nested quantifiers" in result.message.lower()


@pytest.mark.unit
class TestThreadSafetyForRegex:
    """Tests for thread-safe regex timeout handling.

    These tests verify that the regex timeout mechanism works correctly
    when called from non-main threads, which is common in web servers
    and async frameworks.
    """

    def test_regex_search_works_from_worker_thread(self) -> None:
        """Verify regex search works correctly when called from a worker thread."""
        import re
        import threading

        evaluator = ServiceInvariantEvaluator()
        results: list[tuple[bool, re.Match[str] | None, str]] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                # Should work correctly from non-main thread
                success, match, error_msg = evaluator._safe_regex_search(
                    r"\d+", "abc123def"
                )
                results.append((success, match, error_msg))
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5.0)

        assert not errors, f"Worker thread raised: {errors}"
        assert len(results) == 1
        success, match, error_msg = results[0]
        assert success is True
        assert match is not None
        assert match.group() == "123"
        assert error_msg == ""

    def test_dangerous_pattern_rejected_from_worker_thread(self) -> None:
        """Verify dangerous patterns are rejected when called from worker thread."""
        import re
        import threading

        evaluator = ServiceInvariantEvaluator()
        results: list[tuple[bool, re.Match[str] | None, str]] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                # Dangerous pattern should be rejected
                success, match, error_msg = evaluator._safe_regex_search(
                    r"(a+)+", "aaaaaa"
                )
                results.append((success, match, error_msg))
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5.0)

        assert not errors, f"Worker thread raised: {errors}"
        assert len(results) == 1
        success, match, error_msg = results[0]
        assert success is False
        assert match is None
        assert "nested quantifiers" in error_msg.lower()

    def test_field_value_pattern_works_from_worker_thread(self) -> None:
        """Verify FIELD_VALUE evaluation works from worker thread."""
        import threading

        evaluator = ServiceInvariantEvaluator()
        results: list[bool] = []
        errors: list[Exception] = []

        invariant = ModelInvariant(
            name="Thread Test",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumInvariantSeverity.WARNING,
            config={
                "field_path": "email",
                "pattern": r"^[a-z]+@[a-z]+\.[a-z]+$",
            },
        )

        def worker() -> None:
            try:
                result = evaluator.evaluate(invariant, {"email": "test@example.com"})
                results.append(result.passed)
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5.0)

        assert not errors, f"Worker thread raised: {errors}"
        assert len(results) == 1
        assert results[0] is True

    def test_multiple_concurrent_threads(self) -> None:
        """Verify multiple concurrent regex operations work correctly."""
        from concurrent.futures import ThreadPoolExecutor

        evaluator = ServiceInvariantEvaluator()
        num_threads = 10

        def worker(thread_id: int) -> tuple[int, bool, str]:
            success, match, _error_msg = evaluator._safe_regex_search(
                r"thread_\d+", f"prefix_thread_{thread_id}_suffix"
            )
            return (thread_id, success, match.group() if match else "")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            results = [f.result(timeout=10.0) for f in futures]

        # All threads should succeed
        for thread_id, success, matched in results:
            assert success is True, f"Thread {thread_id} failed"
            assert matched == f"thread_{thread_id}", f"Thread {thread_id} wrong match"

    def test_thread_uses_executor_timeout_not_signal(self) -> None:
        """Verify that non-main threads use ThreadPoolExecutor timeout, not signal.

        This test verifies the fix for the critical thread-safety issue where
        signal.signal() would raise ValueError in non-main threads.
        """
        import re
        import threading

        evaluator = ServiceInvariantEvaluator()
        signal_errors: list[Exception] = []
        results: list[tuple[bool, re.Match[str] | None, str]] = []

        def worker() -> None:
            try:
                # This should NOT raise ValueError about signal
                # because the implementation should detect non-main thread
                # and use ThreadPoolExecutor instead
                success, match, error_msg = evaluator._safe_regex_search(
                    r"test", "test string"
                )
                results.append((success, match, error_msg))
            except ValueError as e:
                if "signal only works in main thread" in str(e):
                    signal_errors.append(e)
                raise

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=5.0)

        # No signal-related errors should occur
        assert not signal_errors, (
            f"Signal was incorrectly used in non-main thread: {signal_errors}"
        )
        assert len(results) == 1
        success, _match, _error_msg = results[0]
        assert success is True
