"""
Comprehensive tests for ONEX pattern exclusion decorators.

Tests cover:
- ONEXPatternExclusion class functionality
- Pattern-specific decorators (allow_any_type, allow_dict_str_any, etc.)
- Generic pattern exclusion decorator
- Pattern checking utility functions
- File-based exclusion detection
- Edge cases and complex scenarios

Target: 85%+ coverage for decorators/pattern_exclusions.py
"""

import tempfile
from pathlib import Path

import pytest

from omnibase_core.decorators.pattern_exclusions import (
    ONEXPatternExclusion,
    allow_any_type,
    allow_dict_str_any,
    allow_legacy_pattern,
    allow_mixed_types,
    exclude_from_onex_standards,
    get_exclusion_info,
    has_pattern_exclusion,
    is_excluded_from_pattern_check,
)


class TestONEXPatternExclusionClass:
    """Test the ONEXPatternExclusion class."""

    def test_basic_initialization(self):
        """Test basic ONEXPatternExclusion initialization."""
        exclusion = ONEXPatternExclusion(
            excluded_patterns={"any_type", "dict_str_any"},
            reason="Testing pattern exclusions",
            scope="function",
            reviewer="test_reviewer",
        )

        assert exclusion.excluded_patterns == {"any_type", "dict_str_any"}
        assert exclusion.reason == "Testing pattern exclusions"
        assert exclusion.scope == "function"
        assert exclusion.reviewer == "test_reviewer"

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        exclusion = ONEXPatternExclusion(
            excluded_patterns={"any_type"},
            reason="Test reason",
        )

        assert exclusion.excluded_patterns == {"any_type"}
        assert exclusion.reason == "Test reason"
        assert exclusion.scope == "function"
        assert exclusion.reviewer is None

    def test_apply_to_function(self):
        """Test applying exclusion decorator to a function."""
        exclusion = ONEXPatternExclusion(
            excluded_patterns={"any_type"},
            reason="Test function needs Any type",
        )

        @exclusion
        def test_function():
            return "test"

        # Verify exclusion metadata is attached
        assert hasattr(test_function, "_onex_pattern_exclusions")
        assert "any_type" in test_function._onex_pattern_exclusions
        assert test_function._onex_exclusion_reason == "Test function needs Any type"
        assert test_function._onex_exclusion_scope == "function"

    def test_apply_to_class(self):
        """Test applying exclusion decorator to a class."""
        exclusion = ONEXPatternExclusion(
            excluded_patterns={"dict_str_any"},
            reason="Class uses dynamic dictionaries",
            scope="class",
        )

        @exclusion
        class TestClass:
            pass

        # Verify exclusion metadata is attached to class
        assert hasattr(TestClass, "_onex_pattern_exclusions")
        assert "dict_str_any" in TestClass._onex_pattern_exclusions
        assert TestClass._onex_exclusion_scope == "class"

    def test_multiple_pattern_exclusions(self):
        """Test applying multiple pattern exclusions."""
        exclusion1 = ONEXPatternExclusion(
            excluded_patterns={"any_type"},
            reason="First exclusion",
        )

        exclusion2 = ONEXPatternExclusion(
            excluded_patterns={"dict_str_any"},
            reason="Second exclusion",
        )

        @exclusion1
        @exclusion2
        def test_function():
            return "test"

        # Both patterns should be excluded
        assert "any_type" in test_function._onex_pattern_exclusions
        assert "dict_str_any" in test_function._onex_pattern_exclusions

    def test_overlapping_pattern_exclusions(self):
        """Test applying same pattern multiple times."""
        exclusion1 = ONEXPatternExclusion(
            excluded_patterns={"any_type", "dict_str_any"},
            reason="First exclusion",
        )

        exclusion2 = ONEXPatternExclusion(
            excluded_patterns={"any_type", "logging_call"},
            reason="Second exclusion",
        )

        @exclusion1
        @exclusion2
        def test_function():
            return "test"

        # Should have union of all patterns
        assert "any_type" in test_function._onex_pattern_exclusions
        assert "dict_str_any" in test_function._onex_pattern_exclusions
        assert "logging_call" in test_function._onex_pattern_exclusions


class TestAllowAnyType:
    """Test allow_any_type decorator."""

    def test_allow_any_type_basic(self):
        """Test basic allow_any_type decorator."""

        @allow_any_type("Runtime data with unknown structure")
        def process_dynamic_data(data):
            return data

        assert has_pattern_exclusion(process_dynamic_data, "any_type")
        assert process_dynamic_data._onex_exclusion_reason == (
            "Runtime data with unknown structure"
        )

    def test_allow_any_type_with_reviewer(self):
        """Test allow_any_type with reviewer."""

        @allow_any_type("External API response", reviewer="senior_architect")
        def handle_api_response(response):
            return response

        assert has_pattern_exclusion(handle_api_response, "any_type")
        assert handle_api_response._onex_exclusion_reviewer == "senior_architect"

    def test_allow_any_type_function_still_works(self):
        """Test that decorated function still executes normally."""

        @allow_any_type("Test data")
        def double_value(x):
            return x * 2

        assert double_value(5) == 10
        assert double_value("hello") == "hellohello"


class TestAllowDictStrAny:
    """Test allow_dict_str_any decorator."""

    def test_allow_dict_str_any_basic(self):
        """Test basic allow_dict_str_any decorator."""

        @allow_dict_str_any("Statistics summary with mixed types")
        def get_stats():
            return {"count": 10, "average": 5.5, "valid": True}

        assert has_pattern_exclusion(get_stats, "dict_str_any")
        assert "Statistics summary" in get_stats._onex_exclusion_reason

    def test_allow_dict_str_any_with_reviewer(self):
        """Test allow_dict_str_any with reviewer approval."""

        @allow_dict_str_any("Legacy API compatibility", reviewer="tech_lead")
        def legacy_endpoint():
            return {}

        assert has_pattern_exclusion(legacy_endpoint, "dict_str_any")
        assert legacy_endpoint._onex_exclusion_reviewer == "tech_lead"


class TestAllowMixedTypes:
    """Test allow_mixed_types decorator."""

    def test_allow_mixed_types_basic(self):
        """Test that allow_mixed_types excludes both patterns."""

        @allow_mixed_types("Legacy adapter interface")
        def legacy_adapter(data):
            return {"result": data}

        assert has_pattern_exclusion(legacy_adapter, "any_type")
        assert has_pattern_exclusion(legacy_adapter, "dict_str_any")

    def test_allow_mixed_types_with_reviewer(self):
        """Test allow_mixed_types with reviewer."""

        @allow_mixed_types("Migration period compatibility", reviewer="architect")
        def compatibility_layer():
            pass

        assert compatibility_layer._onex_exclusion_reviewer == "architect"


class TestAllowLegacyPattern:
    """Test allow_legacy_pattern decorator."""

    def test_allow_legacy_pattern_basic(self):
        """Test basic allow_legacy_pattern usage."""

        @allow_legacy_pattern("print_statement", "Development debugging")
        def debug_function():
            print("Debug output")

        assert has_pattern_exclusion(debug_function, "print_statement")

    def test_allow_legacy_pattern_custom_patterns(self):
        """Test allow_legacy_pattern with various custom patterns."""
        patterns = [
            ("logging_call", "Legacy logging system"),
            ("string_literal", "Hardcoded strings for testing"),
            ("global_variable", "Module-level state"),
        ]

        for pattern, reason in patterns:

            @allow_legacy_pattern(pattern, reason)
            def test_func():
                pass

            assert has_pattern_exclusion(test_func, pattern)
            assert test_func._onex_exclusion_reason == reason


class TestExcludeFromOnexStandards:
    """Test the generic exclude_from_onex_standards decorator."""

    def test_exclude_single_pattern(self):
        """Test excluding a single pattern."""

        @exclude_from_onex_standards("any_type", reason="Plugin system")
        def plugin_loader():
            pass

        assert has_pattern_exclusion(plugin_loader, "any_type")

    def test_exclude_multiple_patterns(self):
        """Test excluding multiple patterns at once."""

        @exclude_from_onex_standards(
            "any_type",
            "dict_str_any",
            "dynamic_import",
            reason="Plugin system requires dynamic handling",
            reviewer="senior_architect",
        )
        def dynamic_plugin_loader():
            pass

        assert has_pattern_exclusion(dynamic_plugin_loader, "any_type")
        assert has_pattern_exclusion(dynamic_plugin_loader, "dict_str_any")
        assert has_pattern_exclusion(dynamic_plugin_loader, "dynamic_import")
        assert dynamic_plugin_loader._onex_exclusion_reviewer == "senior_architect"

    def test_exclude_empty_patterns(self):
        """Test behavior with empty pattern list."""

        @exclude_from_onex_standards(reason="No patterns excluded")
        def test_function():
            pass

        # Should have empty exclusion set
        assert hasattr(test_function, "_onex_pattern_exclusions")
        assert len(test_function._onex_pattern_exclusions) == 0


class TestHasPatternExclusion:
    """Test has_pattern_exclusion utility function."""

    def test_has_pattern_exclusion_true(self):
        """Test detection of excluded pattern."""

        @allow_any_type("Test reason")
        def test_function():
            pass

        assert has_pattern_exclusion(test_function, "any_type") is True

    def test_has_pattern_exclusion_false(self):
        """Test detection when pattern not excluded."""

        @allow_any_type("Test reason")
        def test_function():
            pass

        assert has_pattern_exclusion(test_function, "dict_str_any") is False

    def test_has_pattern_exclusion_no_exclusions(self):
        """Test detection on function with no exclusions."""

        def plain_function():
            pass

        assert has_pattern_exclusion(plain_function, "any_type") is False
        assert has_pattern_exclusion(plain_function, "dict_str_any") is False

    def test_has_pattern_exclusion_on_class(self):
        """Test pattern exclusion detection on classes."""

        @allow_dict_str_any("Class uses dynamic data")
        class TestClass:
            pass

        assert has_pattern_exclusion(TestClass, "dict_str_any") is True
        assert has_pattern_exclusion(TestClass, "any_type") is False


class TestGetExclusionInfo:
    """Test get_exclusion_info utility function."""

    def test_get_exclusion_info_complete(self):
        """Test getting complete exclusion information."""

        @exclude_from_onex_standards(
            "any_type",
            "dict_str_any",
            reason="Plugin interface",
            reviewer="architect",
        )
        def plugin_function():
            pass

        info = get_exclusion_info(plugin_function)

        assert info is not None
        assert "any_type" in info["excluded_patterns"]
        assert "dict_str_any" in info["excluded_patterns"]
        assert info["reason"] == "Plugin interface"
        assert info["scope"] == "function"
        assert info["reviewer"] == "architect"

    def test_get_exclusion_info_minimal(self):
        """Test getting exclusion info with minimal metadata."""

        @allow_any_type("Simple reason")
        def simple_function():
            pass

        info = get_exclusion_info(simple_function)

        assert info is not None
        assert "any_type" in info["excluded_patterns"]
        assert info["reason"] == "Simple reason"
        assert info["reviewer"] is None

    def test_get_exclusion_info_none(self):
        """Test getting info from function with no exclusions."""

        def no_exclusions():
            pass

        info = get_exclusion_info(no_exclusions)
        assert info is None

    def test_get_exclusion_info_on_class(self):
        """Test getting exclusion info from a class."""

        @allow_mixed_types("Class interface", reviewer="tech_lead")
        class ExcludedClass:
            pass

        info = get_exclusion_info(ExcludedClass)

        assert info is not None
        assert "any_type" in info["excluded_patterns"]
        assert "dict_str_any" in info["excluded_patterns"]
        assert info["reviewer"] == "tech_lead"


class TestIsExcludedFromPatternCheck:
    """Test is_excluded_from_pattern_check file-based utility."""

    def test_exclusion_via_decorator_in_file(self):
        """Test detection of exclusion via decorator in source file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
@allow_any_type("Test exclusion")
def test_function(data: Any):
    return data
"""
            )
            f.flush()
            temp_path = f.name

        try:
            # Line 3 should be excluded (in function with @allow_any_type)
            result = is_excluded_from_pattern_check(temp_path, 3, "any_type")
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_exclusion_via_inline_comment(self):
        """Test detection of exclusion via inline comment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def process_data():
    data: Any = get_data()  # ONEX_EXCLUDE: any_type
    return data
"""
            )
            f.flush()
            temp_path = f.name

        try:
            result = is_excluded_from_pattern_check(temp_path, 3, "any_type")
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_exclusion_via_exclude_all_comment(self):
        """Test detection via ONEX_EXCLUDE_ALL comment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def legacy_function():
    # ONEX_EXCLUDE_ALL
    result: Dict[str, Any] = {}
    return result
"""
            )
            f.flush()
            temp_path = f.name

        try:
            result = is_excluded_from_pattern_check(temp_path, 4, "dict_str_any")
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_no_exclusion_in_file(self):
        """Test detection when no exclusion present."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def regular_function():
    result: str = "test"
    return result
"""
            )
            f.flush()
            temp_path = f.name

        try:
            result = is_excluded_from_pattern_check(temp_path, 3, "any_type")
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_file_not_found(self):
        """Test behavior when file doesn't exist."""
        result = is_excluded_from_pattern_check(
            "/nonexistent/file.py",
            10,
            "any_type",
        )
        assert result is False

    def test_lookback_range(self):
        """Test that function looks back up to 20 lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Write decorator followed by function
            f.write("# Header line 1\n")
            f.write("# Header line 2\n")
            f.write("@allow_dict_str_any('Test')\n")  # Line 3
            f.write("def test_function():\n")  # Line 4
            for i in range(10):
                f.write(f"    line_{i} = {i}\n")
            f.flush()
            temp_path = f.name

        try:
            # Line 5 is close to decorator (within lookback range)
            result_within_range = is_excluded_from_pattern_check(
                temp_path,
                5,
                "dict_str_any",
            )
            # Should find the decorator looking backward
            assert result_within_range is True
        finally:
            Path(temp_path).unlink()

    def test_unicode_handling(self):
        """Test that function handles unicode in files."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(
                """
# 测试函数 with unicode
@allow_any_type("Unicode test: 你好")
def test_function():
    data = "🚀"  # ONEX_EXCLUDE: any_type
    return data
"""
            )
            f.flush()
            temp_path = f.name

        try:
            result = is_excluded_from_pattern_check(temp_path, 5, "any_type")
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_malformed_file_handling(self):
        """Test graceful handling of malformed files."""
        # Test with invalid line number
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test(): pass\n")
            f.flush()
            temp_path = f.name

        try:
            # Line number way beyond file length
            result = is_excluded_from_pattern_check(temp_path, 1000, "any_type")
            assert result is False
        finally:
            Path(temp_path).unlink()


class TestEdgeCasesAndComplexScenarios:
    """Test edge cases and complex decorator scenarios."""

    def test_decorator_preserves_function_callable(self):
        """Test that decorated functions remain callable."""

        @allow_any_type("Test")
        def add(a, b):
            return a + b

        assert callable(add)
        assert add(2, 3) == 5

    def test_decorator_on_method(self):
        """Test decorator on class methods."""

        class DataProcessor:
            @allow_dict_str_any("Method uses dynamic data")
            def process(self, data):
                return data

        processor = DataProcessor()
        assert has_pattern_exclusion(processor.process, "dict_str_any")
        assert processor.process({"key": "value"}) == {"key": "value"}

    def test_decorator_on_staticmethod(self):
        """Test decorator on static methods."""

        class Utils:
            @staticmethod
            @allow_any_type("Static utility")
            def transform(data):
                return data

        assert callable(Utils.transform)
        assert Utils.transform("test") == "test"

    def test_decorator_on_classmethod(self):
        """Test decorator on class methods."""

        class Factory:
            @classmethod
            @allow_mixed_types("Factory method")
            def create(cls, config):
                return cls()

        assert callable(Factory.create)
        instance = Factory.create({})
        assert isinstance(instance, Factory)

    def test_nested_class_decoration(self):
        """Test decoration on nested classes."""

        @allow_dict_str_any("Outer class")
        class OuterClass:
            @allow_any_type("Inner class")
            class InnerClass:
                pass

        assert has_pattern_exclusion(OuterClass, "dict_str_any")
        assert has_pattern_exclusion(OuterClass.InnerClass, "any_type")

    def test_exclusion_metadata_doesnt_interfere(self):
        """Test that exclusion metadata doesn't interfere with normal operation."""

        @allow_any_type("Test")
        def function_with_docstring():
            """This is a docstring."""
            return 42

        assert function_with_docstring() == 42
        assert function_with_docstring.__doc__ == "This is a docstring."

    def test_multiple_decorators_order(self):
        """Test that decorator order doesn't matter for pattern accumulation."""

        @allow_any_type("First")
        @allow_dict_str_any("Second")
        def func1():
            pass

        @allow_dict_str_any("Second")
        @allow_any_type("First")
        def func2():
            pass

        # Both should have both exclusions regardless of order
        assert has_pattern_exclusion(func1, "any_type")
        assert has_pattern_exclusion(func1, "dict_str_any")
        assert has_pattern_exclusion(func2, "any_type")
        assert has_pattern_exclusion(func2, "dict_str_any")

    def test_exclusion_with_empty_reason(self):
        """Test exclusion with empty reason string."""

        @allow_any_type("")
        def test_function():
            pass

        info = get_exclusion_info(test_function)
        assert info is not None
        assert info["reason"] == ""

    def test_case_sensitivity_in_comments(self):
        """Test that inline comment checking is case-sensitive."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def test_function():
    # onex_exclude: any_type (lowercase)
    data = get_data()
    return data
"""
            )
            f.flush()
            temp_path = f.name

        try:
            # Should not match because comment is lowercase
            result = is_excluded_from_pattern_check(temp_path, 4, "any_type")
            # Actually it should be False because we're looking for ONEX_EXCLUDE (uppercase)
            assert result is False
        finally:
            Path(temp_path).unlink()
