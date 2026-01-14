"""
Tests for AnyTypeVisitor - AST visitor for detecting Any type usage patterns.

This module provides comprehensive tests for the AnyTypeVisitor class,
covering:
- Import detection (from typing import Any)
- Annotation detection (param: Any, -> Any)
- Subscript detection (dict[str, Any], list[Any])
- Union detection (Union[..., Any], X | Any)
- Decorator exemption handling
- Suppression pattern handling
- Edge cases and nested structures

Ticket: OMN-1291
"""

import ast
import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.validation.checker_visitor_any_type import (
    EXEMPT_DECORATORS,
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
    AnyTypeVisitor,
)

# =============================================================================
# Test Helpers
# =============================================================================


def create_visitor(
    source: str,
    suppression_patterns: list[str] | None = None,
    severity: EnumSeverity = EnumSeverity.ERROR,
) -> AnyTypeVisitor:
    """Create and run an AnyTypeVisitor on the given source code."""
    source = textwrap.dedent(source).strip()
    source_lines = source.splitlines()

    visitor = AnyTypeVisitor(
        source_lines=source_lines,
        suppression_patterns=suppression_patterns or [],
        file_path=Path("test.py"),
        severity=severity,
    )

    tree = ast.parse(source)
    visitor.visit(tree)
    return visitor


def get_issues_by_rule(visitor: AnyTypeVisitor, rule_id: str) -> list:
    """Get issues filtered by rule ID."""
    return [i for i in visitor.issues if i.code == rule_id]


# =============================================================================
# Constants Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorConstants:
    """Tests for module constants."""

    def test_rule_constants(self) -> None:
        """Test that rule constants have expected values."""
        assert RULE_ANY_IMPORT == "any_import"
        assert RULE_ANY_ANNOTATION == "any_annotation"
        assert RULE_DICT_STR_ANY == "dict_str_any"
        assert RULE_LIST_ANY == "list_any"
        assert RULE_UNION_WITH_ANY == "union_with_any"

    def test_exempt_decorators(self) -> None:
        """Test that exempt decorators are defined."""
        assert "allow_any_type" in EXEMPT_DECORATORS
        assert "allow_dict_any" in EXEMPT_DECORATORS
        assert isinstance(EXEMPT_DECORATORS, frozenset)


# =============================================================================
# Import Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorImportDetection:
    """Tests for Any import detection."""

    def test_detects_from_typing_import_any(self) -> None:
        """Test detection of 'from typing import Any'."""
        source = """
        from typing import Any
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 1
        assert "Import of 'Any'" in issues[0].message

    def test_detects_any_among_multiple_imports(self) -> None:
        """Test detection of Any when imported with other types."""
        source = """
        from typing import List, Any, Dict, Optional
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 1

    def test_ignores_typing_module_import(self) -> None:
        """Test that 'import typing' alone is not flagged."""
        source = """
        import typing
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 0

    def test_ignores_other_typing_imports(self) -> None:
        """Test that other typing imports are not flagged."""
        source = """
        from typing import List, Dict, Optional, Union
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 0


# =============================================================================
# Annotation Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorAnnotationDetection:
    """Tests for Any annotation detection."""

    def test_detects_any_in_parameter(self) -> None:
        """Test detection of Any in function parameter."""
        source = """
        from typing import Any
        def foo(param: Any) -> None:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1
        assert any("parameter 'param'" in i.message for i in issues)

    def test_detects_any_in_return_type(self) -> None:
        """Test detection of Any in return type."""
        source = """
        from typing import Any
        def foo() -> Any:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1
        assert any("return type" in i.message for i in issues)

    def test_detects_any_in_variable(self) -> None:
        """Test detection of Any in variable annotation."""
        source = """
        from typing import Any
        value: Any = None
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1
        assert any("variable 'value'" in i.message for i in issues)

    def test_detects_typing_any_attribute(self) -> None:
        """Test detection of typing.Any attribute access."""
        source = """
        import typing
        def foo(param: typing.Any) -> None:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1
        assert any("typing.Any" in i.message for i in issues)

    def test_detects_any_in_vararg(self) -> None:
        """Test detection of Any in *args."""
        source = """
        from typing import Any
        def foo(*args: Any) -> None:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1

    def test_detects_any_in_kwarg(self) -> None:
        """Test detection of Any in **kwargs."""
        source = """
        from typing import Any
        def foo(**kwargs: Any) -> None:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(issues) >= 1


# =============================================================================
# dict[str, Any] Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorDictDetection:
    """Tests for dict[str, Any] pattern detection."""

    def test_detects_dict_str_any_builtin(self) -> None:
        """Test detection of dict[str, Any] using builtin dict."""
        source = """
        from typing import Any
        def foo() -> dict[str, Any]:
            return {}
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(issues) >= 1

    def test_detects_typing_dict_any(self) -> None:
        """Test detection of Dict[str, Any] using typing.Dict."""
        source = """
        from typing import Any, Dict
        def foo() -> Dict[str, Any]:
            return {}
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(issues) >= 1

    def test_ignores_dict_with_typed_values(self) -> None:
        """Test that dict[str, int] is not flagged."""
        source = """
        def foo() -> dict[str, int]:
            return {}
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(issues) == 0

    def test_detects_dict_any_in_parameter(self) -> None:
        """Test detection of dict[str, Any] in parameter."""
        source = """
        from typing import Any
        def foo(data: dict[str, Any]) -> None:
            pass
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(issues) >= 1


# =============================================================================
# list[Any] Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorListDetection:
    """Tests for list[Any] pattern detection."""

    def test_detects_list_any_builtin(self) -> None:
        """Test detection of list[Any] using builtin list."""
        source = """
        from typing import Any
        def foo() -> list[Any]:
            return []
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_LIST_ANY)
        assert len(issues) >= 1

    def test_detects_typing_list_any(self) -> None:
        """Test detection of List[Any] using typing.List."""
        source = """
        from typing import Any, List
        def foo() -> List[Any]:
            return []
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_LIST_ANY)
        assert len(issues) >= 1

    def test_ignores_list_with_typed_elements(self) -> None:
        """Test that list[int] is not flagged."""
        source = """
        def foo() -> list[int]:
            return []
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_LIST_ANY)
        assert len(issues) == 0


# =============================================================================
# Union Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorUnionDetection:
    """Tests for Union[..., Any] pattern detection."""

    def test_detects_union_with_any(self) -> None:
        """Test detection of Union[str, Any]."""
        source = """
        from typing import Any, Union
        def foo() -> Union[str, Any]:
            return ""
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_UNION_WITH_ANY)
        assert len(issues) >= 1

    def test_detects_pipe_union_with_any(self) -> None:
        """Test detection of str | Any (PEP 604 syntax)."""
        source = """
        from typing import Any
        def foo() -> str | Any:
            return ""
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_UNION_WITH_ANY)
        assert len(issues) >= 1

    def test_detects_optional_any(self) -> None:
        """Test detection of Optional[Any]."""
        source = """
        from typing import Any, Optional
        def foo() -> Optional[Any]:
            return None
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_UNION_WITH_ANY)
        assert len(issues) >= 1

    def test_detects_any_in_complex_union(self) -> None:
        """Test detection of Any in complex union types."""
        source = """
        from typing import Any
        def foo() -> str | int | Any | None:
            return ""
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_UNION_WITH_ANY)
        assert len(issues) >= 1

    def test_ignores_union_without_any(self) -> None:
        """Test that Union without Any is not flagged."""
        source = """
        from typing import Union
        def foo() -> Union[str, int]:
            return ""
        """
        visitor = create_visitor(source)

        issues = get_issues_by_rule(visitor, RULE_UNION_WITH_ANY)
        assert len(issues) == 0


# =============================================================================
# Decorator Exemption Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorDecoratorExemptions:
    """Tests for decorator-based exemptions."""

    def test_allow_any_type_exempts_function(self) -> None:
        """Test that @allow_any_type exempts function."""
        source = """
        from typing import Any

        def allow_any_type(func):
            return func

        @allow_any_type
        def foo(param: Any) -> Any:
            return param
        """
        visitor = create_visitor(source)

        # Only import should be flagged, not annotations
        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) == 0

    def test_allow_dict_any_exempts_function(self) -> None:
        """Test that @allow_dict_any exempts function."""
        source = """
        from typing import Any

        def allow_dict_any(func):
            return func

        @allow_dict_any
        def foo() -> dict[str, Any]:
            return {}
        """
        visitor = create_visitor(source)

        dict_issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(dict_issues) == 0

    def test_allow_any_type_exempts_class(self) -> None:
        """Test that @allow_any_type exempts class methods."""
        source = """
        from typing import Any

        def allow_any_type(cls):
            return cls

        @allow_any_type
        class MyClass:
            def method(self, param: Any) -> Any:
                return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) == 0

    def test_decorator_with_call_syntax(self) -> None:
        """Test that @allow_any_type() with parentheses works."""
        source = """
        from typing import Any

        def allow_any_type(reason=None):
            def decorator(func):
                return func
            return decorator

        @allow_any_type(reason="test")
        def foo(param: Any) -> Any:
            return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) == 0

    def test_non_exempt_decorator_does_not_exempt(self) -> None:
        """Test that other decorators don't exempt functions."""
        source = """
        from typing import Any

        def other_decorator(func):
            return func

        @other_decorator
        def foo(param: Any) -> Any:
            return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) >= 1


# =============================================================================
# Suppression Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorSuppression:
    """Tests for suppression comment handling."""

    def test_suppression_comment_suppresses_issue(self) -> None:
        """Test that suppression comments suppress violations."""
        source = """
        from typing import Any  # noqa:
        """
        visitor = create_visitor(source, suppression_patterns=["# noqa:"])

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 0

    def test_multiple_suppression_patterns(self) -> None:
        """Test that multiple suppression patterns work."""
        source = """
        from typing import Any  # type: ignore
        """
        visitor = create_visitor(
            source, suppression_patterns=["# noqa:", "# type: ignore"]
        )

        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 0

    def test_suppression_on_different_line_does_not_suppress(self) -> None:
        """Test that suppression on different line doesn't suppress."""
        source = """
        # noqa:
        from typing import Any
        """
        visitor = create_visitor(source, suppression_patterns=["# noqa:"])

        # Import is on line 2, suppression on line 1
        issues = get_issues_by_rule(visitor, RULE_ANY_IMPORT)
        assert len(issues) == 1


# =============================================================================
# Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorEdgeCases:
    """Tests for edge cases and complex scenarios."""

    def test_async_function(self) -> None:
        """Test that async functions are handled."""
        source = """
        from typing import Any
        async def foo(param: Any) -> Any:
            return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) >= 1

    def test_nested_function(self) -> None:
        """Test that nested functions are handled."""
        source = """
        from typing import Any
        def outer():
            def inner(param: Any) -> None:
                pass
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) >= 1

    def test_class_method(self) -> None:
        """Test that class methods are handled."""
        source = """
        from typing import Any
        class MyClass:
            def method(self, param: Any) -> Any:
                return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) >= 1

    def test_class_variable(self) -> None:
        """Test that class variables are handled."""
        source = """
        from typing import Any
        class MyClass:
            value: Any = None
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        assert len(annotation_issues) >= 1

    def test_nested_generic(self) -> None:
        """Test that nested generics with Any are detected."""
        source = """
        from typing import Any
        def foo() -> list[dict[str, Any]]:
            return []
        """
        visitor = create_visitor(source)

        dict_issues = get_issues_by_rule(visitor, RULE_DICT_STR_ANY)
        assert len(dict_issues) >= 1

    def test_exempt_decorator_only_affects_decorated_function(self) -> None:
        """Test that exemption only applies to decorated function."""
        source = """
        from typing import Any

        def allow_any_type(func):
            return func

        @allow_any_type
        def exempt_func(param: Any) -> Any:
            return param

        def non_exempt_func(param: Any) -> Any:
            return param
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        # Should have issues from non_exempt_func
        assert len(annotation_issues) >= 2

    def test_exemption_restored_after_function(self) -> None:
        """Test that exemption state is restored after function."""
        source = """
        from typing import Any

        def allow_any_type(func):
            return func

        @allow_any_type
        def exempt_func(param: Any) -> Any:
            return param

        value: Any = None  # Should be flagged
        """
        visitor = create_visitor(source)

        annotation_issues = get_issues_by_rule(visitor, RULE_ANY_ANNOTATION)
        # Should have issue from module-level variable
        assert any("variable 'value'" in i.message for i in annotation_issues)

    def test_empty_source(self) -> None:
        """Test handling of empty source."""
        visitor = create_visitor("")
        assert len(visitor.issues) == 0

    def test_no_typing_usage(self) -> None:
        """Test file with no typing usage."""
        source = """
        def foo() -> str:
            return "hello"
        """
        visitor = create_visitor(source)
        assert len(visitor.issues) == 0


# =============================================================================
# Helper Method Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorHelperMethods:
    """Tests for helper methods."""

    def test_is_suppressed_valid_line(self) -> None:
        """Test _is_suppressed with valid line number."""
        source = """
        line1  # noqa:
        line2
        """
        visitor = AnyTypeVisitor(
            source_lines=textwrap.dedent(source).strip().splitlines(),
            suppression_patterns=["# noqa:"],
            file_path=Path("test.py"),
            severity=EnumSeverity.ERROR,
        )

        assert visitor._is_suppressed(1) is True
        assert visitor._is_suppressed(2) is False

    def test_is_suppressed_invalid_line(self) -> None:
        """Test _is_suppressed with invalid line numbers."""
        visitor = AnyTypeVisitor(
            source_lines=["line1", "line2"],
            suppression_patterns=["# noqa:"],
            file_path=Path("test.py"),
            severity=EnumSeverity.ERROR,
        )

        assert visitor._is_suppressed(0) is False
        assert visitor._is_suppressed(-1) is False
        assert visitor._is_suppressed(999) is False

    def test_is_exempt_decorator_name(self) -> None:
        """Test _is_exempt_decorator with Name node."""
        visitor = AnyTypeVisitor(
            source_lines=[],
            suppression_patterns=[],
            file_path=Path("test.py"),
            severity=EnumSeverity.ERROR,
        )

        name_node = ast.Name(id="allow_any_type")
        assert visitor._is_exempt_decorator(name_node) is True

        other_name = ast.Name(id="other_decorator")
        assert visitor._is_exempt_decorator(other_name) is False

    def test_is_any_type_name(self) -> None:
        """Test _is_any_type with Name node."""
        visitor = AnyTypeVisitor(
            source_lines=[],
            suppression_patterns=[],
            file_path=Path("test.py"),
            severity=EnumSeverity.ERROR,
        )

        any_name = ast.Name(id="Any")
        assert visitor._is_any_type(any_name) is True

        other_name = ast.Name(id="str")
        assert visitor._is_any_type(other_name) is False

    def test_get_type_name_name_node(self) -> None:
        """Test _get_type_name with Name node."""
        visitor = AnyTypeVisitor(
            source_lines=[],
            suppression_patterns=[],
            file_path=Path("test.py"),
            severity=EnumSeverity.ERROR,
        )

        name_node = ast.Name(id="MyType")
        assert visitor._get_type_name(name_node) == "MyType"


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestAnyTypeVisitorImports:
    """Tests for module imports."""

    def test_import_visitor(self) -> None:
        """Test that AnyTypeVisitor can be imported."""
        from omnibase_core.validation.checker_visitor_any_type import AnyTypeVisitor

        assert AnyTypeVisitor is not None

    def test_import_all_exports(self) -> None:
        """Test that all exported symbols can be imported."""
        from omnibase_core.validation.checker_visitor_any_type import (
            EXEMPT_DECORATORS,
            RULE_ANY_ANNOTATION,
            RULE_ANY_IMPORT,
            RULE_DICT_STR_ANY,
            RULE_LIST_ANY,
            RULE_UNION_WITH_ANY,
            AnyTypeVisitor,
        )

        assert AnyTypeVisitor is not None
        assert RULE_ANY_IMPORT is not None
        assert RULE_ANY_ANNOTATION is not None
        assert RULE_DICT_STR_ANY is not None
        assert RULE_LIST_ANY is not None
        assert RULE_UNION_WITH_ANY is not None
        assert EXEMPT_DECORATORS is not None
