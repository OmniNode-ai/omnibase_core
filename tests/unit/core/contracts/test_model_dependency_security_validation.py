#!/usr/bin/env python3
"""
Comprehensive Security Tests for ModelDependency Validation.

Tests all security aspects of ModelDependency validation as requested in PR #19 feedback:
- Path traversal prevention
- Shell injection protection
- Edge cases for malformed input
- Performance impact of security validation
"""

import pytest
from pydantic import ValidationError

from omnibase_core.core.contracts.model_dependency import (
    EnumDependencyType,
    ModelDependency,
)
from omnibase_core.core.errors.core_errors import OnexError


class TestModelDependencySecurityValidation:
    """Comprehensive security validation tests for ModelDependency."""

    def test_path_traversal_prevention(self) -> None:
        """Test prevention of path traversal attacks in module paths."""

        # Test basic path traversal patterns
        malicious_paths = [
            "../etc/passwd",
            "../../admin/config",
            "module/../../../system",
            "valid.module/../dangerous",
            "..\\windows\\system32",
            "module\\..\\..\\admin",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDependency", module=malicious_path)

            # Verify specific security violation is detected
            assert "security violations detected" in str(exc_info.value).lower()
            error_context = exc_info.value.context
            assert "context" in error_context
            assert "security_violations" in error_context["context"]
            violations = error_context["context"]["security_violations"]
            assert (
                "parent_directory_traversal" in violations
                or "directory_separator_found" in violations
            )

    def test_directory_separator_prevention(self) -> None:
        """Test prevention of directory separators in module paths."""

        invalid_separators = [
            "module/submodule",
            "module\\submodule",
            "valid.module/dangerous.path",
            "module\\dangerous\\path",
            "/absolute/path",
            "\\absolute\\path",
        ]

        for invalid_path in invalid_separators:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDependency", module=invalid_path)

            error_context = exc_info.value.context
            assert (
                "directory_separator_found"
                in error_context["context"]["security_violations"]
            )

    def test_shell_injection_prevention(self) -> None:
        """Test prevention of shell injection characters in module paths."""

        malicious_characters = [
            "module;rm -rf /",
            "module`ls -la`",
            "module$USER",
            "module&whoami",
            "module|cat /etc/passwd",
            "module<script>",
            "module>output.txt",
        ]

        for malicious_path in malicious_characters:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDependency", module=malicious_path)

            error_context = exc_info.value.context
            assert (
                "shell_injection_characters"
                in error_context["context"]["security_violations"]
            )

    def test_relative_path_prevention(self) -> None:
        """Test prevention of relative paths starting with dots."""

        relative_paths = [
            ".hidden_module",
            ".config.secret",
            "./../dangerous",
            "..secret_access",
        ]

        for relative_path in relative_paths:
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDependency", module=relative_path)

            error_context = exc_info.value.context
            violations = error_context["context"]["security_violations"]
            assert (
                "relative_path_start" in violations
                or "parent_directory_traversal" in violations
            )

    def test_excessive_length_prevention(self) -> None:
        """Test prevention of excessively long module paths (DoS protection)."""

        # Generate a module path longer than 200 characters
        long_module = "a" * 201

        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="TestDependency", module=long_module)

        error_context = exc_info.value.context
        assert "excessive_length" in error_context["context"]["security_violations"]

    def test_valid_module_paths_allowed(self) -> None:
        """Test that valid module paths are correctly allowed."""

        valid_paths = [
            "omnibase_core.models.example",
            "mymodule",
            "my_module",
            "my-module",
            "module1.submodule2",
            "a.b.c.d.e",
            "module_with_underscores",
            "module-with-hyphens",
            "Module123",
            "module.Sub_Module-Name",
        ]

        for valid_path in valid_paths:
            # Should not raise any exception
            dependency = ModelDependency(name="TestDependency", module=valid_path)
            assert dependency.module == valid_path

    def test_multiple_security_violations(self) -> None:
        """Test detection of multiple security violations in single path."""

        # Path with multiple violations: relative start + path traversal + shell injection
        malicious_path = "./../../../admin;rm -rf /"

        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="TestDependency", module=malicious_path)

        error_context = exc_info.value.context
        violations = error_context["context"]["security_violations"]

        # Should detect multiple violations
        expected_violations = {
            "relative_path_start",
            "parent_directory_traversal",
            "directory_separator_found",
            "shell_injection_characters",
        }

        # At least 3 of these should be detected
        detected_violations = set(violations)
        assert len(detected_violations.intersection(expected_violations)) >= 3

    def test_security_error_message_quality(self) -> None:
        """Test that security error messages provide helpful information."""

        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="TestDependency", module="../malicious/path")

        error = exc_info.value

        # Verify error message contains security information
        assert "Security violations detected" in error.message
        assert "context" in error.context
        assert "security_violations" in error.context["context"]
        assert "recommendation" in error.context["context"]

        # Verify recommendation is helpful
        recommendation = error.context["context"]["recommendation"]
        assert "alphanumeric" in recommendation
        assert "underscores" in recommendation or "hyphens" in recommendation

    def test_empty_and_whitespace_handling(self) -> None:
        """Test proper handling of empty and whitespace-only module paths."""

        # Empty and whitespace paths should return None (valid)
        empty_cases = [
            None,
            "",
            "   ",
            "\t",
            "\n",
            " \t \n ",
        ]

        for empty_case in empty_cases:
            dependency = ModelDependency(name="TestDependency", module=empty_case)
            assert dependency.module is None

    def test_case_sensitivity_security(self) -> None:
        """Test that security validation is case-sensitive where appropriate."""

        # These should all be blocked regardless of case
        case_variants = [
            "../Admin",
            "../ADMIN",
            "Module/Submodule",
            "MODULE\\SUBMODULE",
        ]

        for variant in case_variants:
            with pytest.raises(OnexError):
                ModelDependency(name="TestDependency", module=variant)


class TestModelDependencyPerformanceValidation:
    """Performance tests for ModelDependency security validation."""

    def test_validation_performance_large_valid_input(self) -> None:
        """Test validation performance with large valid input."""
        import time

        # Create a moderately large valid module path (under 200 chars)
        large_valid_path = ".".join(
            [f"module{i}" for i in range(20)]
        )  # ~140 chars, well under limit

        start_time = time.time()

        # Validate 1000 dependencies to test performance
        for i in range(1000):
            ModelDependency(name=f"Dependency{i}", module=large_valid_path)

        end_time = time.time()
        duration = end_time - start_time

        # Validation should complete within 2 seconds for 1000 items
        # (as mentioned in PR feedback performance requirements)
        assert duration < 2.0, f"Validation took {duration:.2f}s, expected < 2.0s"

    def test_validation_performance_malicious_input(self) -> None:
        """Test that malicious input validation doesn't cause performance issues."""
        import time

        malicious_paths = [
            "../" * 50,  # Deep path traversal
            "a" * 300,  # Very long path
            "module" + ";" * 100 + "rm -rf /",  # Many shell injection chars
        ]

        start_time = time.time()

        # Each malicious path should be rejected quickly
        for i in range(100):
            for malicious_path in malicious_paths:
                with pytest.raises(OnexError):
                    ModelDependency(name=f"Dependency{i}", module=malicious_path)

        end_time = time.time()
        duration = end_time - start_time

        # Even malicious input validation should be fast
        assert (
            duration < 1.0
        ), f"Malicious input validation took {duration:.2f}s, expected < 1.0s"


class TestModelDependencyEdgeCases:
    """Edge case tests for ModelDependency validation as requested in PR feedback."""

    def test_unicode_and_international_characters(self) -> None:
        """Test handling of unicode and international characters."""

        unicode_paths = [
            "модуль",  # Cyrillic
            "模块",  # Chinese
            "モジュール",  # Japanese
            "módulo",  # Spanish with accent
            "mödule",  # German umlaut
        ]

        for unicode_path in unicode_paths:
            # Unicode characters should be rejected by our pattern
            with pytest.raises(OnexError) as exc_info:
                ModelDependency(name="TestDependency", module=unicode_path)

            # Should fail on pattern validation, not security
            assert "Invalid module path format" in str(exc_info.value)

    def test_boundary_conditions(self) -> None:
        """Test boundary conditions for path length and character limits."""

        # Test exactly at the 200 character boundary
        # Use invalid pattern (starts with number) to test pattern validation at boundaries
        path_199_invalid = "1" + "a" * 198  # Starts with digit - invalid pattern
        path_200_invalid = "1" + "a" * 199  # Starts with digit - invalid pattern
        path_201 = "a" * 201  # Valid pattern but too long

        # 199 and 200 should be allowed by length check but fail pattern
        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="Test", module=path_199_invalid)
        assert "Invalid module path format" in str(exc_info.value)

        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="Test", module=path_200_invalid)
        assert "Invalid module path format" in str(exc_info.value)

        # 201 should fail on excessive length
        with pytest.raises(OnexError) as exc_info:
            ModelDependency(name="Test", module=path_201)
        error_context = exc_info.value.context
        assert "excessive_length" in error_context["context"]["security_violations"]

    def test_mixed_valid_invalid_segments(self) -> None:
        """Test module paths with mixed valid and invalid segments."""

        mixed_paths = [
            "valid.module.../invalid",
            "good_module.bad/../segment",
            "valid.123invalid",  # Number start is invalid
            "valid.-invalid",  # Hyphen at start is invalid
            "valid._invalid",  # Underscore at start is invalid
            # Note: Hyphens and underscores at end are actually valid in Python module names
            # so "valid.invalid-" and "valid.invalid_" are not included as they don't fail
        ]

        for mixed_path in mixed_paths:
            with pytest.raises(OnexError):
                ModelDependency(name="TestDependency", module=mixed_path)

    def test_regex_pattern_edge_cases(self) -> None:
        """Test edge cases in regex pattern matching."""

        # Test valid edge cases that should work
        valid_edge_cases = [
            "a",  # Single character
            "a.b",  # Minimum two segments
            "A",  # Single uppercase
            "Module123",  # Numbers at end
            "module_123",  # Underscore with numbers
            "module-123",  # Hyphen with numbers
        ]

        for valid_case in valid_edge_cases:
            dependency = ModelDependency(name="TestDependency", module=valid_case)
            assert dependency.module == valid_case

        # Test invalid edge cases
        invalid_edge_cases = [
            "",  # Empty string (should return None, not fail)
            "123module",  # Number at start
            "-module",  # Hyphen at start
            "_module",  # Underscore at start
            # Note: "module-" and "module_" are actually valid according to current regex
            # Python allows trailing underscores in module names
            "module..double",  # Double dots
            ".module",  # Dot at start
            "module.",  # Dot at end
        ]

        for invalid_case in invalid_edge_cases:
            if invalid_case == "":
                # Empty string should return None, not raise error
                dependency = ModelDependency(name="TestDependency", module=invalid_case)
                assert dependency.module is None
            else:
                with pytest.raises(OnexError):
                    ModelDependency(name="TestDependency", module=invalid_case)
