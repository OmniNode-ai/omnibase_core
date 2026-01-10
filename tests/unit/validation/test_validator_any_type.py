"""
Tests for ValidatorAnyType - AST-based validator for Any type usage patterns.

This module provides comprehensive tests for the ValidatorAnyType class,
covering:
- Detection of Any type imports
- Detection of Any in type annotations
- Detection of dict[str, Any] patterns
- Detection of list[Any] patterns
- Detection of Union[..., Any] patterns
- Exemption handling via decorators
- Suppression comment handling
- Contract loading

Ticket: OMN-1291
"""

import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_any_type import ValidatorAnyType
from omnibase_core.validation.visitor_any_type import (
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
)

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_contract(
    suppression_comments: list[str] | None = None,
    severity_default: EnumValidationSeverity = EnumValidationSeverity.ERROR,
) -> ModelValidatorSubcontract:
    """Create a test contract for ValidatorAnyType."""
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="any_type",
        validator_name="Any Type Policy Validator",
        validator_description="Test validator for Any type usage",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=suppression_comments or ["# noqa:"],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=severity_default,
    )


def write_python_file(tmp_path: Path, content: str, filename: str = "test.py") -> Path:
    """Write Python content to a temporary file."""
    file_path = tmp_path / filename
    file_path.write_text(textwrap.dedent(content).strip())
    return file_path


# =============================================================================
# ValidatorAnyType Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeInit:
    """Tests for ValidatorAnyType initialization."""

    def test_validator_id(self) -> None:
        """Test that validator_id is set correctly."""
        assert ValidatorAnyType.validator_id == "any_type"

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)

        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract."""
        validator = ValidatorAnyType()
        # Contract is loaded lazily, so _contract is None initially
        assert validator._contract is None


# =============================================================================
# Any Import Detection Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeImportDetection:
    """Tests for Any import detection."""

    def test_detects_any_import(self, tmp_path: Path) -> None:
        """Test detection of 'from typing import Any'."""
        source = """
        from typing import Any

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        assert len(result.issues) >= 1
        any_import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(any_import_issues) == 1
        assert "Import of 'Any'" in any_import_issues[0].message

    def test_ignores_other_typing_imports(self, tmp_path: Path) -> None:
        """Test that other typing imports are not flagged."""
        source = """
        from typing import Optional, List, Dict, Union

        def foo() -> Optional[str]:
            return None
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # No Any imports
        any_import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(any_import_issues) == 0


# =============================================================================
# Any Annotation Detection Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeAnnotationDetection:
    """Tests for Any type annotation detection."""

    def test_detects_any_parameter(self, tmp_path: Path) -> None:
        """Test detection of Any in function parameters."""
        source = """
        from typing import Any

        def foo(param: Any) -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1

    def test_detects_any_return_type(self, tmp_path: Path) -> None:
        """Test detection of Any in return type."""
        source = """
        from typing import Any

        def foo() -> Any:
            return None
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1

    def test_detects_any_variable(self, tmp_path: Path) -> None:
        """Test detection of Any in variable annotations."""
        source = """
        from typing import Any

        value: Any = None
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1

    def test_detects_typing_any_attribute(self, tmp_path: Path) -> None:
        """Test detection of typing.Any."""
        source = """
        import typing

        def foo(param: typing.Any) -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1


# =============================================================================
# dict[str, Any] Detection Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeDictDetection:
    """Tests for dict[str, Any] pattern detection."""

    def test_detects_dict_str_any(self, tmp_path: Path) -> None:
        """Test detection of dict[str, Any]."""
        source = """
        from typing import Any

        def foo() -> dict[str, Any]:
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        dict_issues = [i for i in result.issues if i.code == RULE_DICT_STR_ANY]
        assert len(dict_issues) >= 1

    def test_detects_typing_dict_any(self, tmp_path: Path) -> None:
        """Test detection of Dict[str, Any] (typing.Dict)."""
        source = """
        from typing import Any, Dict

        def foo() -> Dict[str, Any]:
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        dict_issues = [i for i in result.issues if i.code == RULE_DICT_STR_ANY]
        assert len(dict_issues) >= 1

    def test_ignores_typed_dict_values(self, tmp_path: Path) -> None:
        """Test that dict[str, int] is not flagged."""
        source = """
        def foo() -> dict[str, int]:
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        dict_issues = [i for i in result.issues if i.code == RULE_DICT_STR_ANY]
        assert len(dict_issues) == 0


# =============================================================================
# list[Any] Detection Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeListDetection:
    """Tests for list[Any] pattern detection."""

    def test_detects_list_any(self, tmp_path: Path) -> None:
        """Test detection of list[Any]."""
        source = """
        from typing import Any

        def foo() -> list[Any]:
            return []
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        list_issues = [i for i in result.issues if i.code == RULE_LIST_ANY]
        assert len(list_issues) >= 1

    def test_ignores_typed_list_elements(self, tmp_path: Path) -> None:
        """Test that list[int] is not flagged."""
        source = """
        def foo() -> list[int]:
            return []
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        list_issues = [i for i in result.issues if i.code == RULE_LIST_ANY]
        assert len(list_issues) == 0


# =============================================================================
# Union with Any Detection Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeUnionDetection:
    """Tests for Union[..., Any] pattern detection."""

    def test_detects_union_with_any(self, tmp_path: Path) -> None:
        """Test detection of Union[str, Any]."""
        source = """
        from typing import Any, Union

        def foo() -> Union[str, Any]:
            return ""
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        union_issues = [i for i in result.issues if i.code == RULE_UNION_WITH_ANY]
        assert len(union_issues) >= 1

    def test_detects_pipe_union_with_any(self, tmp_path: Path) -> None:
        """Test detection of str | Any (PEP 604 syntax)."""
        source = """
        from typing import Any

        def foo() -> str | Any:
            return ""
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        union_issues = [i for i in result.issues if i.code == RULE_UNION_WITH_ANY]
        assert len(union_issues) >= 1

    def test_detects_optional_any(self, tmp_path: Path) -> None:
        """Test detection of Optional[Any]."""
        source = """
        from typing import Any, Optional

        def foo() -> Optional[Any]:
            return None
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        union_issues = [i for i in result.issues if i.code == RULE_UNION_WITH_ANY]
        assert len(union_issues) >= 1


# =============================================================================
# Decorator Exemption Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeDecoratorExemptions:
    """Tests for decorator-based exemptions."""

    def test_allow_any_type_decorator_exempts_function(self, tmp_path: Path) -> None:
        """Test that @allow_any_type decorator exempts function."""
        source = """
        from typing import Any

        def allow_any_type(func):
            return func

        @allow_any_type
        def foo(param: Any) -> Any:
            return param
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # Only the import should be flagged, not the annotations
        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) == 0

    def test_allow_dict_any_decorator_exempts_function(self, tmp_path: Path) -> None:
        """Test that @allow_dict_any decorator exempts function."""
        source = """
        from typing import Any

        def allow_dict_any(func):
            return func

        @allow_dict_any
        def foo() -> dict[str, Any]:
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # dict[str, Any] should be exempted
        dict_issues = [i for i in result.issues if i.code == RULE_DICT_STR_ANY]
        assert len(dict_issues) == 0


# =============================================================================
# Suppression Comment Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeSuppressionComments:
    """Tests for suppression comment handling."""

    def test_suppression_comment_suppresses_violation(self, tmp_path: Path) -> None:
        """Test that suppression comments suppress violations."""
        source = """
        from typing import Any  # noqa:

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract(suppression_comments=["# noqa:"])
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The import should be suppressed
        import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(import_issues) == 0

    def test_custom_suppression_pattern(self, tmp_path: Path) -> None:
        """Test that custom suppression patterns work."""
        source = """
        from typing import Any  # ONEX_EXCLUDE: any_type

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract(
            suppression_comments=["# ONEX_EXCLUDE: any_type"]
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The import should be suppressed
        import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(import_issues) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        """Test that syntax errors are handled gracefully."""
        source = """
        def foo(
            # Missing closing paren
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # Should not crash, just return empty issues
        assert result.is_valid

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that empty files are handled."""
        file_path = write_python_file(tmp_path, "")

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        assert result.is_valid
        assert len(result.issues) == 0

    def test_handles_async_functions(self, tmp_path: Path) -> None:
        """Test that async functions are analyzed."""
        source = """
        from typing import Any

        async def foo(param: Any) -> Any:
            return param
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1

    def test_handles_class_methods(self, tmp_path: Path) -> None:
        """Test that class methods are analyzed."""
        source = """
        from typing import Any

        class MyClass:
            def method(self, param: Any) -> Any:
                return param
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1

    def test_handles_nested_functions(self, tmp_path: Path) -> None:
        """Test that nested functions are analyzed."""
        source = """
        from typing import Any

        def outer():
            def inner(param: Any) -> None:
                pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1


# =============================================================================
# Validate Directory Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeDirectory:
    """Tests for directory validation."""

    def test_validates_multiple_files(self, tmp_path: Path) -> None:
        """Test validation of multiple files in a directory."""
        # Create multiple files
        write_python_file(
            tmp_path,
            "from typing import Any\ndef foo(x: Any): pass",
            "file1.py",
        )
        write_python_file(
            tmp_path,
            "from typing import Any\ndef bar() -> Any: pass",
            "file2.py",
        )
        write_python_file(
            tmp_path,
            "def clean() -> str: return ''",
            "file3.py",
        )

        contract = create_test_contract()
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate(tmp_path)

        # Should find issues in file1 and file2
        assert len(result.issues) >= 2


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeImports:
    """Tests for module imports."""

    def test_import_validator(self) -> None:
        """Test that ValidatorAnyType can be imported."""
        from omnibase_core.validation.validator_any_type import ValidatorAnyType

        assert ValidatorAnyType is not None

    def test_import_rule_constants(self) -> None:
        """Test that rule constants can be imported."""
        from omnibase_core.validation.validator_any_type import (
            RULE_ANY_ANNOTATION,
            RULE_ANY_IMPORT,
            RULE_DICT_STR_ANY,
            RULE_LIST_ANY,
            RULE_UNION_WITH_ANY,
        )

        assert RULE_ANY_IMPORT == "any_import"
        assert RULE_ANY_ANNOTATION == "any_annotation"
        assert RULE_DICT_STR_ANY == "dict_str_any"
        assert RULE_LIST_ANY == "list_any"
        assert RULE_UNION_WITH_ANY == "union_with_any"

    def test_import_from_validation_package(self) -> None:
        """Test that ValidatorAnyType can be imported from validation package."""
        from omnibase_core.validation import ValidatorAnyType

        assert ValidatorAnyType is not None
