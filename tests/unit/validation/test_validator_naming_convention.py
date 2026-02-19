# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ValidatorNamingConvention - Contract-driven naming convention validator.

This module provides comprehensive tests for the ValidatorNamingConvention class,
covering:
- File naming convention validation
- Class naming validation (PascalCase)
- Function naming validation (snake_case)
- Anti-pattern detection
- Exemptions for allowed files and prefixes
- Suppression comment handling
- Contract loading

Ticket: OMN-1291
"""

import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_naming_convention import (
    RULE_CLASS_NAMING,
    RULE_FILE_NAMING,
    RULE_FUNCTION_NAMING,
    RULE_UNKNOWN_NAMING,
    ValidatorNamingConvention,
)

# =============================================================================
# Test Helpers
# =============================================================================


def create_test_contract(
    suppression_comments: list[str] | None = None,
    severity_default: EnumSeverity = EnumSeverity.ERROR,
    rules: list[ModelValidatorRule] | None = None,
) -> ModelValidatorSubcontract:
    """Create a test contract for ValidatorNamingConvention.

    Note: Rules must be explicitly defined since missing rules default to disabled
    per validator_base.py:615 alignment (OMN-1291 PR #360).
    """
    default_rules = [
        ModelValidatorRule(
            rule_id=RULE_FILE_NAMING,
            description="Validates file naming conventions",
            severity=EnumSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_CLASS_NAMING,
            description="Validates class naming (PascalCase)",
            severity=EnumSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_FUNCTION_NAMING,
            description="Validates function naming (snake_case)",
            severity=EnumSeverity.ERROR,
            enabled=True,
        ),
        ModelValidatorRule(
            rule_id=RULE_UNKNOWN_NAMING,
            description="Catch-all for unknown naming issues",
            severity=EnumSeverity.WARNING,
            enabled=True,
        ),
    ]
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="naming_convention",
        validator_name="Naming Convention Validator",
        validator_description="Test validator for naming conventions",
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


def create_omnibase_structure(tmp_path: Path, subdir: str) -> Path:
    """Create a mock omnibase_core directory structure."""
    omnibase_dir = tmp_path / "src" / "omnibase_core" / subdir
    omnibase_dir.mkdir(parents=True, exist_ok=True)
    return omnibase_dir


# =============================================================================
# ValidatorNamingConvention Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionInit:
    """Tests for ValidatorNamingConvention initialization."""

    def test_validator_id(self) -> None:
        """Test that validator_id is set correctly."""
        assert ValidatorNamingConvention.validator_id == "naming_convention"

    def test_init_with_contract(self) -> None:
        """Test initialization with a pre-loaded contract."""
        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)

        assert validator.contract is contract

    def test_init_without_contract(self) -> None:
        """Test initialization without a contract (lazy loading behavior).

        When no contract is provided, the validator should still be created
        successfully and will load the contract lazily when needed.
        """
        validator = ValidatorNamingConvention()
        # Verify validator is properly initialized with correct class-level ID
        assert validator.validator_id == "naming_convention"
        # Verify the validator can perform validation (triggering lazy contract load)
        # by checking that it has the expected rule constants
        from omnibase_core.validation.validator_naming_convention import (
            RULE_CLASS_NAMING,
            RULE_FILE_NAMING,
            RULE_FUNCTION_NAMING,
        )

        assert RULE_FILE_NAMING == "file_naming"
        assert RULE_CLASS_NAMING == "class_naming"
        assert RULE_FUNCTION_NAMING == "function_naming"


# =============================================================================
# File Naming Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionFileNaming:
    """Tests for file naming convention validation."""

    def test_allowed_files_not_flagged(self, tmp_path: Path) -> None:
        """Test that allowed files like __init__.py are not flagged."""
        omnibase_dir = create_omnibase_structure(tmp_path, "models")
        init_file = omnibase_dir / "__init__.py"
        init_file.write_text("# init file")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(init_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 0

    def test_conftest_not_flagged(self, tmp_path: Path) -> None:
        """Test that conftest.py is not flagged."""
        omnibase_dir = create_omnibase_structure(tmp_path, "tests")
        conftest_file = omnibase_dir / "conftest.py"
        conftest_file.write_text("# conftest")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(conftest_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 0

    def test_private_module_not_flagged(self, tmp_path: Path) -> None:
        """Test that private modules starting with _ are not flagged."""
        omnibase_dir = create_omnibase_structure(tmp_path, "utils")
        private_file = omnibase_dir / "_internal.py"
        private_file.write_text("# private")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(private_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 0

    def test_correctly_prefixed_model_file(self, tmp_path: Path) -> None:
        """Test that correctly prefixed files are not flagged."""
        omnibase_dir = create_omnibase_structure(tmp_path, "models")
        model_file = omnibase_dir / "model_example.py"
        model_file.write_text("# model")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(model_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 0

    def test_incorrectly_prefixed_model_file(self, tmp_path: Path) -> None:
        """Test that incorrectly prefixed files are flagged."""
        omnibase_dir = create_omnibase_structure(tmp_path, "models")
        bad_file = omnibase_dir / "example_model.py"  # Wrong order
        bad_file.write_text("# bad model")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(bad_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 1


# =============================================================================
# Class Naming Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionClassNaming:
    """Tests for class naming convention validation."""

    def test_pascal_case_class_not_flagged(self, tmp_path: Path) -> None:
        """Test that PascalCase class names are not flagged."""
        source = """
        class MyExampleClass:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        assert len(class_naming_issues) == 0

    def test_lowercase_class_flagged(self, tmp_path: Path) -> None:
        """Test that lowercase class names are flagged."""
        source = """
        class my_example_class:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        assert len(class_naming_issues) >= 1

    def test_mixedcase_class_flagged(self, tmp_path: Path) -> None:
        """Test that mixedCase class names (not PascalCase) are flagged.

        Class names must start with an uppercase letter to follow PascalCase.
        'myClass' starts with lowercase 'm', so it should be flagged.
        """
        source = """
        class myClass:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        # myClass starts with lowercase, violating PascalCase - should be flagged
        assert len(class_naming_issues) >= 1, (
            "Expected class naming issue for 'myClass' which starts with lowercase"
        )


# =============================================================================
# Function Naming Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionFunctionNaming:
    """Tests for function naming convention validation."""

    def test_snake_case_function_not_flagged(self, tmp_path: Path) -> None:
        """Test that snake_case function names are not flagged."""
        source = """
        def my_example_function():
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        function_naming_issues = [
            i for i in result.issues if i.code == RULE_FUNCTION_NAMING
        ]
        assert len(function_naming_issues) == 0

    def test_camel_case_function_flagged(self, tmp_path: Path) -> None:
        """Test that camelCase function names are flagged."""
        source = """
        def myExampleFunction():
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        function_naming_issues = [
            i for i in result.issues if i.code == RULE_FUNCTION_NAMING
        ]
        assert len(function_naming_issues) >= 1

    def test_async_function_analyzed(self, tmp_path: Path) -> None:
        """Test that async function names are analyzed."""
        source = """
        async def myAsyncFunction():
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        function_naming_issues = [
            i for i in result.issues if i.code == RULE_FUNCTION_NAMING
        ]
        # Should detect camelCase in async function
        assert len(function_naming_issues) >= 1


# =============================================================================
# Rule Enablement Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionRuleEnablement:
    """Tests for selective rule enablement."""

    def test_disable_file_naming_rule(self, tmp_path: Path) -> None:
        """Test that file naming rule can be disabled."""
        omnibase_dir = create_omnibase_structure(tmp_path, "models")
        bad_file = omnibase_dir / "example_model.py"
        bad_file.write_text("# bad model")

        rules = [
            ModelValidatorRule(
                rule_id=RULE_FILE_NAMING,
                description="File naming",
                enabled=False,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(bad_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        assert len(file_naming_issues) == 0

    def test_disable_class_naming_rule(self, tmp_path: Path) -> None:
        """Test that class naming rule can be disabled."""
        source = """
        class my_bad_class:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_CLASS_NAMING,
                description="Class naming",
                enabled=False,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        assert len(class_naming_issues) == 0

    def test_disable_function_naming_rule(self, tmp_path: Path) -> None:
        """Test that function naming rule can be disabled."""
        source = """
        def myBadFunction():
            pass
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_FUNCTION_NAMING,
                description="Function naming",
                enabled=False,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        function_naming_issues = [
            i for i in result.issues if i.code == RULE_FUNCTION_NAMING
        ]
        assert len(function_naming_issues) == 0


# =============================================================================
# Severity Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionSeverity:
    """Tests for severity configuration."""

    def test_custom_rule_severity(self, tmp_path: Path) -> None:
        """Test that custom severity can be set per rule."""
        source = """
        class my_bad_class:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        rules = [
            ModelValidatorRule(
                rule_id=RULE_CLASS_NAMING,
                description="Class naming",
                enabled=True,
                severity=EnumSeverity.WARNING,
            )
        ]
        contract = create_test_contract(rules=rules)
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        # Lowercase class name should be flagged
        assert len(class_naming_issues) >= 1, (
            "Expected class naming issue for lowercase class name"
        )
        # Custom severity should be applied
        assert class_naming_issues[0].severity == EnumSeverity.WARNING


# =============================================================================
# Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        """Test that syntax errors are handled gracefully.

        When a file has syntax errors, the validator should:
        1. Not raise an exception
        2. Return a valid result object
        3. Mark the result as valid (no naming issues can be detected in unparseable code)
        """
        source = """
        def foo(
            # Missing closing paren
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        # Validator should return a result without crashing
        assert result is not None
        # When AST parsing fails, validator should return valid result (no issues detected)
        # because naming convention violations cannot be detected in unparseable code
        assert result.is_valid, (
            "Syntax error files should return valid (no issues detected)"
        )

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that empty files are handled."""
        file_path = write_python_file(tmp_path, "")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        assert result.is_valid

    def test_handles_non_python_file_name(self, tmp_path: Path) -> None:
        """Test handling of non-Python files."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("Not a Python file")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)

        # Should not flag non-.py files
        file_naming_issues = [
            i
            for i in validator.validate_file(text_file).issues
            if i.code == RULE_FILE_NAMING
        ]
        assert len(file_naming_issues) == 0

    def test_handles_nested_classes(self, tmp_path: Path) -> None:
        """Test that nested classes are analyzed."""
        source = """
        class OuterClass:
            class inner_class:
                pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        # inner_class should be flagged
        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        assert len(class_naming_issues) >= 1

    def test_handles_method_names(self, tmp_path: Path) -> None:
        """Test that method names are analyzed."""
        source = """
        class MyClass:
            def myBadMethod(self):
                pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        # myBadMethod should be flagged
        function_naming_issues = [
            i for i in result.issues if i.code == RULE_FUNCTION_NAMING
        ]
        assert len(function_naming_issues) >= 1


# =============================================================================
# Suppression Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionSuppression:
    """Tests for suppression comment handling."""

    def test_suppression_comment_suppresses_class_issue(self, tmp_path: Path) -> None:
        """Test that suppression comments work for class naming issues."""
        source = """
        class my_bad_class:  # noqa:
            pass
        """
        file_path = write_python_file(tmp_path, source)

        contract = create_test_contract(suppression_comments=["# noqa:"])
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(file_path)

        # The class naming issue should be suppressed
        class_naming_issues = [i for i in result.issues if i.code == RULE_CLASS_NAMING]
        assert len(class_naming_issues) == 0


# =============================================================================
# Suggestion Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionSuggestions:
    """Tests for suggestion generation."""

    def test_file_naming_suggestion_generated(self, tmp_path: Path) -> None:
        """Test that suggestions are generated for file naming issues."""
        omnibase_dir = create_omnibase_structure(tmp_path, "models")
        bad_file = omnibase_dir / "example.py"  # Missing model_ prefix
        bad_file.write_text("# content")

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate_file(bad_file)

        file_naming_issues = [i for i in result.issues if i.code == RULE_FILE_NAMING]
        # File in models/ without required prefix should be flagged
        assert len(file_naming_issues) >= 1, (
            "Expected file naming issue for file without required prefix"
        )
        # Issue should have a suggestion for fixing
        assert file_naming_issues[0].suggestion is not None


# =============================================================================
# Validate Directory Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionDirectory:
    """Tests for directory validation."""

    def test_validates_multiple_files(self, tmp_path: Path) -> None:
        """Test validation of multiple files in a directory."""
        # Create files with different issues
        write_python_file(
            tmp_path,
            "class bad_class:\n    pass",
            "file1.py",
        )
        write_python_file(
            tmp_path,
            "def badFunction():\n    pass",
            "file2.py",
        )
        write_python_file(
            tmp_path,
            "class GoodClass:\n    def good_method(self):\n        pass",
            "file3.py",
        )

        contract = create_test_contract()
        validator = ValidatorNamingConvention(contract=contract)
        result = validator.validate(tmp_path)

        # Should find issues in file1 and file2
        assert len(result.issues) >= 2


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestValidatorNamingConventionImports:
    """Tests for module imports."""

    def test_import_validator(self) -> None:
        """Test that ValidatorNamingConvention can be imported."""
        from omnibase_core.validation.validator_naming_convention import (
            ValidatorNamingConvention,
        )

        assert ValidatorNamingConvention is not None

    def test_import_rule_constants(self) -> None:
        """Test that rule constants can be imported."""
        from omnibase_core.validation.validator_naming_convention import (
            RULE_CLASS_NAMING,
            RULE_FILE_NAMING,
            RULE_FUNCTION_NAMING,
            RULE_UNKNOWN_NAMING,
        )

        assert RULE_FILE_NAMING == "file_naming"
        assert RULE_CLASS_NAMING == "class_naming"
        assert RULE_FUNCTION_NAMING == "function_naming"
        assert RULE_UNKNOWN_NAMING == "unknown_naming"

    def test_import_from_validation_package(self) -> None:
        """Test that ValidatorNamingConvention can be imported from validation package."""
        from omnibase_core.validation import ValidatorNamingConvention

        assert ValidatorNamingConvention is not None
