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
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.checker_visitor_any_type import (
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
)
from omnibase_core.validation.validator_any_type import ValidatorAnyType

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_contract(
    suppression_comments: list[str] | None = None,
    severity_default: EnumValidationSeverity = EnumValidationSeverity.ERROR,
    rules: list[ModelValidatorRule] | None = None,
) -> ModelValidatorSubcontract:
    """Create a test contract for ValidatorAnyType.

    Note: Rules must be explicitly defined since missing rules default to disabled
    per validator_base.py:615 alignment (OMN-1291 PR #360).
    """
    default_rules = [
        ModelValidatorRule(
            rule_id=RULE_ANY_IMPORT,
            description="Detects 'from typing import Any' statements",
            severity=EnumValidationSeverity.WARNING,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_ANY_ANNOTATION,
            description="Detects Any in type annotations",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_DICT_STR_ANY,
            description="Detects dict[str, Any] usage",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_LIST_ANY,
            description="Detects list[Any] usage",
            severity=EnumValidationSeverity.WARNING,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_UNION_WITH_ANY,
            description="Detects Union[..., Any] or ... | Any",
            severity=EnumValidationSeverity.ERROR,
            enabled=True,
        ),
    ]
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
        rules=rules if rules is not None else default_rules,
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
        """Test initialization without a contract (lazy loading behavior).

        When no contract is provided, the validator should still be created
        successfully and will load the contract lazily when needed.
        """
        validator = ValidatorAnyType()
        # Validator should be created successfully without a contract
        # The contract will be loaded lazily when first accessed via the property
        assert validator is not None
        assert validator.validator_id == "any_type"


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


# =============================================================================
# Per-Rule Configuration Tests
# =============================================================================


def create_test_contract_with_rules(
    rules: list[tuple[str, bool, EnumValidationSeverity]],
    severity_default: EnumValidationSeverity = EnumValidationSeverity.ERROR,
) -> ModelValidatorSubcontract:
    """Create a test contract with specific rule configurations.

    Args:
        rules: List of tuples (rule_id, enabled, severity).
        severity_default: Default severity for rules not in the list.

    Returns:
        ModelValidatorSubcontract with the specified rules.
    """
    from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
        ModelValidatorRule,
    )

    rule_models = [
        ModelValidatorRule(
            rule_id=rule_id,
            description=f"Test rule {rule_id}",
            enabled=enabled,
            severity=severity,
        )
        for rule_id, enabled, severity in rules
    ]

    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="any_type",
        validator_name="Any Type Policy Validator",
        validator_description="Test validator for Any type usage",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=["# noqa:"],
        fail_on_error=True,
        fail_on_warning=False,
        severity_default=severity_default,
        rules=rule_models,
    )


@pytest.mark.unit
class TestValidatorAnyTypePerRuleConfiguration:
    """Tests for per-rule enablement and severity overrides."""

    def test_disabled_rule_is_skipped(self, tmp_path: Path) -> None:
        """Test that disabled rules do not produce issues."""
        source = """
        from typing import Any

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        # Disable the any_import rule
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, False, EnumValidationSeverity.ERROR),
            ]
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The import should NOT be flagged because the rule is disabled
        any_import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(any_import_issues) == 0

    def test_enabled_rule_produces_issues(self, tmp_path: Path) -> None:
        """Test that enabled rules produce issues."""
        source = """
        from typing import Any

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        # Enable the any_import rule explicitly
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, True, EnumValidationSeverity.ERROR),
            ]
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The import SHOULD be flagged because the rule is enabled
        any_import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(any_import_issues) == 1

    def test_severity_override_from_contract(self, tmp_path: Path) -> None:
        """Test that severity is overridden from contract rules."""
        source = """
        from typing import Any

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        # Override severity to WARNING for any_import rule
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, True, EnumValidationSeverity.WARNING),
            ],
            severity_default=EnumValidationSeverity.ERROR,
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The import issue should have WARNING severity (overridden)
        any_import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(any_import_issues) == 1
        assert any_import_issues[0].severity == EnumValidationSeverity.WARNING

    def test_severity_override_to_critical(self, tmp_path: Path) -> None:
        """Test that severity can be overridden to CRITICAL."""
        source = """
        from typing import Any

        def foo(x: Any) -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        # Override severity to CRITICAL for any_annotation rule
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_ANNOTATION, True, EnumValidationSeverity.CRITICAL),
            ],
            severity_default=EnumValidationSeverity.WARNING,
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # The annotation issue should have CRITICAL severity (overridden)
        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1
        assert annotation_issues[0].severity == EnumValidationSeverity.CRITICAL

    def test_multiple_rules_with_different_configs(self, tmp_path: Path) -> None:
        """Test that multiple rules can have different configurations."""
        source = """
        from typing import Any

        def foo(x: Any) -> dict[str, Any]:
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        # Configure: any_import=disabled, any_annotation=warning, dict_str_any=error
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, False, EnumValidationSeverity.ERROR),  # Disabled
                (RULE_ANY_ANNOTATION, True, EnumValidationSeverity.WARNING),  # Warning
                (RULE_DICT_STR_ANY, True, EnumValidationSeverity.ERROR),  # Error
            ],
            severity_default=EnumValidationSeverity.INFO,
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # any_import should NOT be in issues (disabled)
        import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(import_issues) == 0

        # any_annotation should have WARNING severity
        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1
        assert annotation_issues[0].severity == EnumValidationSeverity.WARNING

        # dict_str_any should have ERROR severity
        dict_issues = [i for i in result.issues if i.code == RULE_DICT_STR_ANY]
        assert len(dict_issues) >= 1
        assert dict_issues[0].severity == EnumValidationSeverity.ERROR

    def test_unconfigured_rule_is_disabled_by_default(self, tmp_path: Path) -> None:
        """Test that rules not in contract are disabled by default.

        Per validator_base.py:615 alignment (OMN-1291 PR #360), missing rules
        default to disabled for consistent contract-driven behavior.
        """
        source = """
        from typing import Any

        def foo() -> list[Any]:
            return []
        """
        file_path = write_python_file(tmp_path, source)

        # Only configure any_import, leave list_any unconfigured
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, True, EnumValidationSeverity.WARNING),
            ],
            severity_default=EnumValidationSeverity.CRITICAL,
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # any_import should be detected (it's configured and enabled)
        import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(import_issues) >= 1
        assert import_issues[0].severity == EnumValidationSeverity.WARNING

        # list_any should NOT be detected (unconfigured = disabled by default)
        list_issues = [i for i in result.issues if i.code == RULE_LIST_ANY]
        assert len(list_issues) == 0

    def test_disable_all_rules_produces_no_issues(self, tmp_path: Path) -> None:
        """Test that disabling all rules produces no issues."""
        source = """
        from typing import Any

        def foo(x: Any) -> dict[str, Any]:
            values: list[Any] = []
            return {}
        """
        file_path = write_python_file(tmp_path, source)

        # Disable all relevant rules
        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, False, EnumValidationSeverity.ERROR),
                (RULE_ANY_ANNOTATION, False, EnumValidationSeverity.ERROR),
                (RULE_DICT_STR_ANY, False, EnumValidationSeverity.ERROR),
                (RULE_LIST_ANY, False, EnumValidationSeverity.ERROR),
                (RULE_UNION_WITH_ANY, False, EnumValidationSeverity.ERROR),
            ]
        )
        validator = ValidatorAnyType(contract=contract)
        result = validator.validate_file(file_path)

        # No issues should be reported
        assert len(result.issues) == 0
        assert result.is_valid


# =============================================================================
# Rule Configuration Cache Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorAnyTypeRuleConfigCache:
    """Tests for rule configuration caching in ValidatorBase."""

    def test_rule_config_cache_is_built_once(self, tmp_path: Path) -> None:
        """Test that rule config cache is built only once."""
        source = """
        from typing import Any

        def foo() -> None:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract_with_rules(
            rules=[
                (RULE_ANY_IMPORT, True, EnumValidationSeverity.WARNING),
            ]
        )
        validator = ValidatorAnyType(contract=contract)

        # Initially, cache should be None
        assert validator._rule_config_cache is None

        # Validate file (triggers cache build)
        validator.validate_file(file_path)

        # Cache should now be populated
        assert validator._rule_config_cache is not None
        assert RULE_ANY_IMPORT in validator._rule_config_cache
        assert validator._rule_config_cache[RULE_ANY_IMPORT] == (
            True,
            EnumValidationSeverity.WARNING,
        )

    def test_rule_config_lookup_is_o1(self, tmp_path: Path) -> None:
        """Test that rule config lookup uses O(1) dictionary access."""
        source = """
        from typing import Any

        def foo() -> Any:
            return None
        """
        file_path = write_python_file(tmp_path, source)

        # Create contract with many rules
        rules = [(f"rule_{i}", True, EnumValidationSeverity.ERROR) for i in range(100)]
        rules.append((RULE_ANY_IMPORT, True, EnumValidationSeverity.WARNING))
        rules.append((RULE_ANY_ANNOTATION, True, EnumValidationSeverity.INFO))

        contract = create_test_contract_with_rules(rules=rules)
        validator = ValidatorAnyType(contract=contract)

        # Validate to build cache
        result = validator.validate_file(file_path)

        # Verify cache contains the rules we care about
        assert validator._rule_config_cache is not None
        assert RULE_ANY_IMPORT in validator._rule_config_cache
        assert RULE_ANY_ANNOTATION in validator._rule_config_cache

        # Verify severity overrides were applied
        import_issues = [i for i in result.issues if i.code == RULE_ANY_IMPORT]
        assert len(import_issues) == 1
        assert import_issues[0].severity == EnumValidationSeverity.WARNING

        annotation_issues = [i for i in result.issues if i.code == RULE_ANY_ANNOTATION]
        assert len(annotation_issues) >= 1
        assert annotation_issues[0].severity == EnumValidationSeverity.INFO
