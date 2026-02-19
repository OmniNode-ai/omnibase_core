# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests to ensure regex patterns stay synchronized across the codebase.

This module verifies that the ERROR_CODE_PATTERN is centralized in
omnibase_core.constants.constants_error and correctly imported by all modules
that use it.

Ticket: OMN-1054
"""

import re

import pytest


@pytest.mark.unit
class TestErrorCodePatternSync:
    """Verify ERROR_CODE_PATTERN is centralized and consistent.

    The ERROR_CODE_PATTERN is now centralized in:
    - omnibase_core.constants.constants_error.ERROR_CODE_PATTERN

    And re-exported from:
    1. omnibase_core.constants (via __init__.py)
    2. omnibase_core.validation.validators.validator_common
    3. omnibase_core.models.context.model_error_metadata

    All locations MUST use the same pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$
    """

    def test_error_code_patterns_are_identical(self) -> None:
        """Verify ERROR_CODE_PATTERN is identical in all locations."""
        from omnibase_core.constants import ERROR_CODE_PATTERN as CONSTANTS_PATTERN
        from omnibase_core.constants.constants_error import (
            ERROR_CODE_PATTERN as SOURCE_PATTERN,
        )
        from omnibase_core.models.context.model_error_metadata import (
            ERROR_CODE_PATTERN as MODEL_PATTERN,
        )
        from omnibase_core.validation.validators.validator_common import (
            ERROR_CODE_PATTERN as VALIDATOR_PATTERN,
        )

        # All patterns should be the exact same object (imported from source)
        assert SOURCE_PATTERN is CONSTANTS_PATTERN, (
            "constants/__init__.py should re-export from constants_error"
        )
        assert SOURCE_PATTERN is MODEL_PATTERN, (
            "model_error_metadata should import from constants_error"
        )
        assert SOURCE_PATTERN is VALIDATOR_PATTERN, (
            "validator_common should import from constants_error"
        )

    def test_retry_error_context_uses_centralized_pattern(self) -> None:
        """Verify model_retry_error_context imports from centralized location."""
        # Import the ERROR_CODE_PATTERN used by model_retry_error_context
        # This is used internally by ModelErrorContext validation
        import omnibase_core.models.context.model_retry_error_context as retry_module
        from omnibase_core.constants.constants_error import (
            ERROR_CODE_PATTERN as SOURCE_PATTERN,
        )

        # Access the pattern used by the module
        retry_pattern = retry_module.ERROR_CODE_PATTERN

        assert SOURCE_PATTERN is retry_pattern, (
            "model_retry_error_context should import ERROR_CODE_PATTERN from constants_error"
        )

    def test_error_code_pattern_expected_value(self) -> None:
        """Verify ERROR_CODE_PATTERN matches the expected specification.

        Expected pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$

        This pattern enforces:
        - Starts with uppercase letter [A-Z]
        - Followed by uppercase letters, digits, or underscores [A-Z0-9_]*
        - Underscore separator before numeric suffix _
        - 1-4 digit numeric suffix \\d{1,4}

        Examples: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001
        """
        from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN

        expected_pattern = r"^[A-Z][A-Z0-9_]*_\d{1,4}$"
        assert ERROR_CODE_PATTERN.pattern == expected_pattern, (
            f"ERROR_CODE_PATTERN has unexpected value!\n"
            f"  Expected: {expected_pattern!r}\n"
            f"  Actual:   {ERROR_CODE_PATTERN.pattern!r}\n"
            f"If intentional change, update constants_error.py and this test."
        )

    def test_error_code_pattern_validates_correctly(self) -> None:
        """Verify ERROR_CODE_PATTERN validates expected cases correctly."""
        from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN

        # Valid patterns
        valid_codes = [
            "AUTH_001",
            "VALIDATION_123",
            "NETWORK_TIMEOUT_001",
            "A_1",
            "X_1234",
            "ERROR404_001",
            "V2_AUTH_99",
        ]
        for code in valid_codes:
            assert ERROR_CODE_PATTERN.match(code), f"Should accept: {code}"

        # Invalid patterns
        invalid_codes = [
            "E001",  # Lint-style (no underscore)
            "auth_001",  # Lowercase
            "AUTH",  # No numeric suffix
            "AUTH_",  # Empty suffix
            "AUTH_12345",  # Too many digits
            "123_001",  # Starts with number
            "AUTH-001",  # Hyphen instead of underscore
        ]
        for code in invalid_codes:
            assert not ERROR_CODE_PATTERN.match(code), f"Should reject: {code}"


@pytest.mark.unit
class TestSemVerPatternSync:
    """Verify _SEMVER_PATTERN stays synchronized across files.

    The _SEMVER_PATTERN is defined in three locations:
    1. omnibase_core.validation.validators.validator_common._SEMVER_PATTERN
    2. omnibase_core.models.context.model_metrics_context._SEMVER_PATTERN
    3. omnibase_core.models.primitives.model_semver._SEMVER_PATTERN

    This duplication exists to avoid circular imports. All three MUST be identical.
    """

    def test_semver_patterns_are_identical(self) -> None:
        """Verify _SEMVER_PATTERN is identical across all locations."""
        # Import from each location
        # Note: We import the module and access the private variable
        import omnibase_core.models.context.model_metrics_context as metrics_module
        import omnibase_core.models.primitives.model_semver as semver_module
        import omnibase_core.validation.validators.validator_common as validators_module

        validator_pattern = validators_module._SEMVER_PATTERN.pattern
        metrics_pattern = metrics_module._SEMVER_PATTERN.pattern
        semver_pattern = semver_module._SEMVER_PATTERN.pattern

        # Check all pairs
        assert validator_pattern == metrics_pattern, (
            f"_SEMVER_PATTERN mismatch detected!\n"
            f"  validator_common.py:      {validator_pattern!r}\n"
            f"  model_metrics_context.py: {metrics_pattern!r}\n"
            f"These patterns MUST be identical. Update all files together."
        )

        assert validator_pattern == semver_pattern, (
            f"_SEMVER_PATTERN mismatch detected!\n"
            f"  validator_common.py: {validator_pattern!r}\n"
            f"  model_semver.py:     {semver_pattern!r}\n"
            f"These patterns MUST be identical. Update all files together."
        )

    def test_semver_pattern_validates_correctly(self) -> None:
        """Verify _SEMVER_PATTERN validates expected cases correctly."""
        import omnibase_core.validation.validators.validator_common as validators_module

        pattern = validators_module._SEMVER_PATTERN

        # Valid versions
        valid_versions = [
            "0.0.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0+build",
            "1.0.0+build.123",
            "1.0.0-alpha+001",
            "1.0.0-beta.1+build.123",
        ]
        for version in valid_versions:
            assert pattern.match(version), f"Should accept: {version}"

        # Invalid versions
        invalid_versions = [
            "1",
            "1.0",
            "v1.0.0",  # Leading v
            "01.0.0",  # Leading zero
            "1.00.0",  # Leading zero
            "1.0.0-",  # Trailing hyphen
            "1.0.0+",  # Trailing plus
            "1.0.0-01",  # Leading zero in prerelease
        ]
        for version in invalid_versions:
            assert not pattern.match(version), f"Should reject: {version}"


@pytest.mark.unit
class TestEventBusErrorCodePatternDocumentation:
    """Document the intentional difference in ModelEventBusOutputState error pattern.

    ModelEventBusOutputState uses a DIFFERENT, simpler pattern for error_code:
    Pattern: ^[A-Z][A-Z0-9_]*$

    This is MORE PERMISSIVE than the standard ERROR_CODE_PATTERN because:
    1. It accepts error codes without the required underscore-digit suffix
    2. It allows codes like "UNKNOWN", "TIMEOUT", etc.
    3. It serves a different use case (event bus status codes vs structured errors)

    However, it enforces that codes must start with an uppercase letter (not a digit
    or underscore), which is consistent with standard error code conventions.

    This test documents and verifies this intentional difference.
    """

    def test_event_bus_pattern_is_simpler(self) -> None:
        """Verify the event bus uses a simpler, more permissive pattern."""
        from omnibase_core.models.event_bus.model_event_bus_output_state import (
            ModelEventBusOutputState,
        )

        # Access the class-level pattern
        event_bus_pattern = ModelEventBusOutputState._ERROR_CODE_PATTERN.pattern
        expected_pattern = r"^[A-Z][A-Z0-9_]*$"

        assert event_bus_pattern == expected_pattern, (
            f"ModelEventBusOutputState._ERROR_CODE_PATTERN changed unexpectedly!\n"
            f"  Expected: {expected_pattern!r}\n"
            f"  Actual:   {event_bus_pattern!r}"
        )

    def test_event_bus_pattern_accepts_simple_codes(self) -> None:
        """Verify the event bus pattern accepts simple status codes."""
        from omnibase_core.models.event_bus.model_event_bus_output_state import (
            ModelEventBusOutputState,
        )

        pattern = ModelEventBusOutputState._ERROR_CODE_PATTERN

        # These are valid for event bus but NOT for standard error codes
        event_bus_codes = [
            "UNKNOWN",
            "TIMEOUT",
            "ERROR",
            "SUCCESS",
            "AUTH_001",  # Also accepts standard format
            "VALIDATION_123",
        ]
        for code in event_bus_codes:
            assert pattern.match(code), f"Event bus should accept: {code}"

    def test_event_bus_pattern_differs_from_standard(self) -> None:
        """Document that event bus and standard patterns are intentionally different."""
        from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN
        from omnibase_core.models.event_bus.model_event_bus_output_state import (
            ModelEventBusOutputState,
        )

        event_bus_pattern = ModelEventBusOutputState._ERROR_CODE_PATTERN.pattern
        standard_pattern = ERROR_CODE_PATTERN.pattern

        assert event_bus_pattern != standard_pattern, (
            "Event bus pattern and standard ERROR_CODE_PATTERN should be DIFFERENT.\n"
            "The event bus uses a simpler pattern for status codes.\n"
            "If you intentionally unified them, update this test."
        )


@pytest.mark.unit
class TestPatternCompilationConsistency:
    """Verify patterns are compiled with consistent flags."""

    def test_error_code_patterns_no_flags(self) -> None:
        """Verify ERROR_CODE_PATTERN is compiled without special flags."""
        from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN

        # Should have default flags (UNICODE only, which is the default)
        assert ERROR_CODE_PATTERN.flags == re.UNICODE, (
            f"ERROR_CODE_PATTERN has unexpected flags: {ERROR_CODE_PATTERN.flags}"
        )

    def test_semver_patterns_no_flags(self) -> None:
        """Verify _SEMVER_PATTERN is compiled without special flags."""
        import omnibase_core.models.context.model_metrics_context as metrics_module
        import omnibase_core.models.primitives.model_semver as semver_module
        import omnibase_core.validation.validators.validator_common as validators_module

        # All should have default flags
        assert validators_module._SEMVER_PATTERN.flags == re.UNICODE
        assert metrics_module._SEMVER_PATTERN.flags == re.UNICODE
        assert semver_module._SEMVER_PATTERN.flags == re.UNICODE
