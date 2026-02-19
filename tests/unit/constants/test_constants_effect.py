# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for constants_effect module.

Tests the security constants and helper functions for template injection protection.

VERSION: 1.0.0
"""

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestDeniedBuiltinsConstant:
    """Test DENIED_BUILTINS frozenset configuration."""

    def test_denied_builtins_is_frozenset(self) -> None:
        """Test that DENIED_BUILTINS is a frozenset (immutable)."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        assert isinstance(DENIED_BUILTINS, frozenset)

    def test_denied_builtins_contains_code_execution_functions(self) -> None:
        """Test that code execution functions are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        code_execution_builtins = {
            "import",
            "__import__",
            "eval",
            "exec",
            "compile",
        }
        for builtin in code_execution_builtins:
            assert builtin in DENIED_BUILTINS, (
                f"Missing code execution builtin: {builtin}"
            )

    def test_denied_builtins_contains_introspection_functions(self) -> None:
        """Test that introspection functions are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        introspection_builtins = {
            "globals",
            "locals",
            "vars",
            "dir",
        }
        for builtin in introspection_builtins:
            assert builtin in DENIED_BUILTINS, (
                f"Missing introspection builtin: {builtin}"
            )

    def test_denied_builtins_contains_attribute_manipulation(self) -> None:
        """Test that attribute manipulation functions are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        attr_builtins = {
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
        }
        for builtin in attr_builtins:
            assert builtin in DENIED_BUILTINS, f"Missing attribute builtin: {builtin}"

    def test_denied_builtins_contains_class_introspection(self) -> None:
        """Test that class/type introspection attributes are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        class_introspection = {
            "__class__",
            "__bases__",
            "__mro__",
            "__subclasses__",
        }
        for attr in class_introspection:
            assert attr in DENIED_BUILTINS, f"Missing class introspection attr: {attr}"

    def test_denied_builtins_contains_object_internals(self) -> None:
        """Test that object internal attributes are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        object_internals = {
            "__dict__",
            "__builtins__",
            "__globals__",
            "__code__",
            "__func__",
            "__self__",
            "__closure__",
        }
        for attr in object_internals:
            assert attr in DENIED_BUILTINS, f"Missing object internal attr: {attr}"

    def test_denied_builtins_contains_dangerous_io_functions(self) -> None:
        """Test that dangerous I/O functions are in the deny-list."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        dangerous_io = {
            "open",
            "input",
            "breakpoint",
        }
        for func in dangerous_io:
            assert func in DENIED_BUILTINS, f"Missing dangerous I/O function: {func}"

    def test_denied_builtins_is_not_empty(self) -> None:
        """Test that DENIED_BUILTINS contains a reasonable number of entries."""
        from omnibase_core.constants.constants_effect import DENIED_BUILTINS

        # Should have at least 50+ entries for comprehensive protection
        assert len(DENIED_BUILTINS) >= 50, (
            f"DENIED_BUILTINS has only {len(DENIED_BUILTINS)} entries, "
            "expected at least 50 for comprehensive protection"
        )


@pytest.mark.unit
class TestContainsDeniedBuiltin:
    """Test contains_denied_builtin helper function."""

    def test_returns_none_for_safe_paths(self) -> None:
        """Test that safe field paths return None (no denied builtin found)."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        safe_paths = [
            "user_id",
            "user.profile.name",
            "config.timeout_ms",
            "data.items.0.value",
            "_private_field",
            "snake_case_name",
            "CamelCaseName",
            "a.b.c.d.e.f",
            "evaluator",  # Contains 'eval' as substring but not exact match
            "compiler_version",  # Contains 'compile' as substring
            "global_config",  # Contains 'global' as substring
        ]

        for path in safe_paths:
            result = contains_denied_builtin(path)
            assert result is None, (
                f"Safe path '{path}' was incorrectly denied: {result}"
            )

    def test_returns_denied_builtin_for_direct_match(self) -> None:
        """Test that direct matches to denied built-ins are caught."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        denied_paths = {
            "eval": "eval",
            "exec": "exec",
            "compile": "compile",
            "__import__": "__import__",
            "globals": "globals",
            "locals": "locals",
            "__class__": "__class__",
            "__dict__": "__dict__",
            "__builtins__": "__builtins__",
            "open": "open",
        }

        for path, expected in denied_paths.items():
            result = contains_denied_builtin(path)
            assert result == expected, (
                f"Path '{path}' should have returned '{expected}', got '{result}'"
            )

    def test_returns_denied_builtin_in_nested_path(self) -> None:
        """Test that denied built-ins in nested paths are caught."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        nested_denied = {
            "user.__class__": "__class__",
            "data.__class__.name": "__class__",
            "obj.__bases__": "__bases__",
            "item.__subclasses__": "__subclasses__",
            "config.eval": "eval",
            "module.__import__": "__import__",
            "request.__globals__": "__globals__",
            "nested.path.__dict__": "__dict__",
            "a.b.c.__builtins__": "__builtins__",
            "deep.nested.open": "open",
        }

        for path, expected in nested_denied.items():
            result = contains_denied_builtin(path)
            assert result == expected, (
                f"Nested path '{path}' should have returned '{expected}', got '{result}'"
            )

    def test_returns_first_denied_builtin_found(self) -> None:
        """Test that the first denied builtin in a path is returned."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        # Path with multiple denied builtins - should return the first one
        path = "eval.__class__.__bases__"
        result = contains_denied_builtin(path)
        assert result == "eval", (
            f"Should return first denied builtin 'eval', got '{result}'"
        )

    def test_case_sensitive_matching(self) -> None:
        """Test that matching is case-sensitive (Python identifiers are case-sensitive)."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        # These should NOT be denied (uppercase variants)
        uppercase_safe = [
            "Eval",
            "EVAL",
            "Exec",
            "EXEC",
            "Globals",
            "GLOBALS",
            "__CLASS__",
            "__DICT__",
        ]

        for path in uppercase_safe:
            result = contains_denied_builtin(path)
            assert result is None, (
                f"Uppercase path '{path}' should be allowed (case-sensitive), "
                f"but was denied: {result}"
            )

    def test_empty_string_returns_none(self) -> None:
        """Test that empty string returns None (no denied builtin)."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        result = contains_denied_builtin("")
        assert result is None

    def test_handles_path_with_only_dots(self) -> None:
        """Test that path with only dots is handled gracefully."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        # These produce empty segments which should not match any denied builtin
        result = contains_denied_builtin("...")
        assert result is None

        result = contains_denied_builtin(".a.b.")
        assert result is None

    def test_handles_single_segment_paths(self) -> None:
        """Test single-segment paths (no dots)."""
        from omnibase_core.constants.constants_effect import contains_denied_builtin

        # Safe single segment
        assert contains_denied_builtin("user_id") is None
        assert contains_denied_builtin("name") is None

        # Denied single segment
        assert contains_denied_builtin("eval") == "eval"
        assert contains_denied_builtin("__class__") == "__class__"


@pytest.mark.unit
class TestSafeFieldPatternAndDeniedBuiltinsInteraction:
    """Test the interaction between SAFE_FIELD_PATTERN and DENIED_BUILTINS.

    These tests verify that the two security mechanisms work together:
    1. SAFE_FIELD_PATTERN validates character sets
    2. DENIED_BUILTINS blocks dangerous identifiers that pass the pattern
    """

    def test_denied_builtins_only_contain_pattern_valid_characters(self) -> None:
        """Verify all denied builtins would pass SAFE_FIELD_PATTERN.

        This confirms that DENIED_BUILTINS provides defense-in-depth by blocking
        dangerous identifiers that would otherwise pass character validation.
        """
        from omnibase_core.constants.constants_effect import (
            DENIED_BUILTINS,
            SAFE_FIELD_PATTERN,
        )

        for builtin in DENIED_BUILTINS:
            # Each denied builtin should match the safe pattern
            # (otherwise the pattern would already block it)
            assert SAFE_FIELD_PATTERN.match(builtin), (
                f"Denied builtin '{builtin}' would be blocked by SAFE_FIELD_PATTERN "
                "before the deny-list check - this is redundant"
            )

    def test_pattern_blocks_attacks_not_in_denylist(self) -> None:
        """Test that SAFE_FIELD_PATTERN blocks attacks not covered by deny-list.

        The pattern blocks special characters, so attacks using parentheses,
        brackets, etc. are caught before the deny-list is even checked.
        """
        from omnibase_core.constants.constants_effect import SAFE_FIELD_PATTERN

        # These should be blocked by the pattern (special characters)
        pattern_blocked = [
            "eval()",
            "__import__('os')",
            "obj['key']",
            "cmd; rm -rf",
            "path/../etc",
            "${template}",
            "foo|bar",
            "foo&bar",
            "foo<bar",
            "foo>bar",
        ]

        for attack in pattern_blocked:
            assert not SAFE_FIELD_PATTERN.match(attack), (
                f"Attack '{attack}' should be blocked by SAFE_FIELD_PATTERN"
            )
