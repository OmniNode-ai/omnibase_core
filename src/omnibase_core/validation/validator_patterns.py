"""
ValidatorPatterns - Contract-driven validator for ONEX code patterns.

This module provides the ValidatorPatterns class for analyzing Python source
code to detect pattern violations that may indicate ONEX compliance issues.

The validator uses AST analysis to find:
- Pydantic model naming violations (must start with 'Model')
- UUID fields using str instead of UUID type
- Category/type/status fields using str instead of enums
- Overly generic function names
- Functions with too many parameters
- God classes with too many methods
- Class and function naming convention violations

Pattern validation tools for ONEX compliance including:
- Pydantic pattern validation
- Generic pattern validation
- Anti-pattern detection
- Naming convention validation

Usage Examples:
    Programmatic usage (new ValidatorBase API)::

        from pathlib import Path
        from omnibase_core.validation import ValidatorPatterns

        validator = ValidatorPatterns()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_patterns src/

    Legacy API::

        from pathlib import Path
        from omnibase_core.validation.validator_patterns import (
            validate_patterns_file,
            validate_patterns_directory,
        )

        issues = validate_patterns_file(Path("myfile.py"))
        result = validate_patterns_directory(Path("src/"))

Thread Safety:
    ValidatorPatterns instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - PydanticPatternChecker: Checker for Pydantic model patterns
    - NamingConventionChecker: Checker for naming conventions
    - GenericPatternChecker: Checker for generic anti-patterns
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import ClassVar, Protocol

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, YAML_PARSING_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_utils import ModelValidationResult

from .checker_generic_pattern import GenericPatternChecker
from .checker_naming_convention import NamingConventionChecker
from .checker_pydantic_pattern import PydanticPatternChecker

# Rule IDs for mapping checker issues to contract rules
RULE_PYDANTIC_PREFIX = "pydantic_model_prefix"
RULE_UUID_FIELD = "uuid_field_type"
RULE_ENUM_FIELD = "enum_field_type"
RULE_ENTITY_NAME = "entity_name_pattern"
RULE_GENERIC_FUNCTION = "generic_function_name"
RULE_MAX_PARAMS = "max_parameters"
RULE_GOD_CLASS = "god_class"
RULE_CLASS_ANTI_PATTERN = "class_anti_pattern"
RULE_CLASS_PASCAL_CASE = "class_pascal_case"
RULE_FUNCTION_SNAKE_CASE = "function_snake_case"


class ProtocolPatternChecker(Protocol):
    """Protocol for pattern checkers with issues tracking."""

    issues: list[str]

    def visit(self, node: ast.AST) -> None:
        """Visit an AST node."""
        ...


def _parse_line_number(issue: str) -> int | None:
    """Extract line number from issue string.

    Issue strings are expected to be in format: "Line N: message"

    Args:
        issue: The issue string to parse.

    Returns:
        Line number if found, None otherwise.
    """
    match = re.match(r"Line (\d+):", issue)
    if match:
        return int(match.group(1))
    return None


def _parse_message(issue: str) -> str:
    """Extract message from issue string.

    Issue strings are expected to be in format: "Line N: message"

    Args:
        issue: The issue string to parse.

    Returns:
        The message part of the issue string.
    """
    match = re.match(r"Line \d+: (.*)", issue)
    if match:
        return match.group(1)
    return issue


def _categorize_issue(issue: str) -> str:
    """Categorize an issue string to a rule ID.

    Maps issue messages to their corresponding rule IDs based on content.

    Args:
        issue: The issue message to categorize.

    Returns:
        The rule ID corresponding to the issue type.
    """
    issue_lower = issue.lower()

    # Pydantic pattern checks
    if "should start with 'model'" in issue_lower:
        return RULE_PYDANTIC_PREFIX
    if "should use uuid type" in issue_lower:
        return RULE_UUID_FIELD
    if "should use enum" in issue_lower:
        return RULE_ENUM_FIELD
    if "might reference an entity" in issue_lower:
        return RULE_ENTITY_NAME

    # Generic pattern checks
    if "is too generic" in issue_lower and "function" in issue_lower:
        return RULE_GENERIC_FUNCTION
    if "parameters" in issue_lower:
        return RULE_MAX_PARAMS
    if "methods" in issue_lower and "breaking into smaller" in issue_lower:
        return RULE_GOD_CLASS

    # Naming convention checks
    if "contains anti-pattern" in issue_lower:
        return RULE_CLASS_ANTI_PATTERN
    if "should use pascalcase" in issue_lower:
        return RULE_CLASS_PASCAL_CASE
    if "should use snake_case" in issue_lower:
        return RULE_FUNCTION_SNAKE_CASE

    # Default to generic pattern if cannot categorize
    return RULE_GENERIC_FUNCTION


class ValidatorPatterns(ValidatorBase):
    """Validator for detecting code pattern violations in Python code.

    This validator uses AST analysis to detect potentially problematic code
    patterns, including:
    - Pydantic model naming violations
    - Type annotation issues (str instead of UUID/enum)
    - Generic function/class naming anti-patterns
    - God classes and functions with too many parameters

    The validator respects exemptions via inline suppression comments
    defined in the contract.

    Attributes:
        validator_id: Unique identifier for this validator ("patterns").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_patterns import ValidatorPatterns
        >>> validator = ValidatorPatterns()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "patterns"

    def _load_contract(self) -> ModelValidatorSubcontract:
        """Load contract from YAML, handling nested 'validation:' structure.

        The contract YAML has the structure:
            contract_kind: validation_subcontract
            validation:
                version: ...
                validator_id: ...
                ...

        This method extracts the nested 'validation' section.

        Returns:
            Loaded ModelValidatorSubcontract instance.

        Raises:
            ModelOnexError: If contract file not found or invalid.
        """
        contract_path = self._get_contract_path()

        if not contract_path.exists():
            raise ModelOnexError(
                message=f"Validator contract not found: {contract_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                },
            )

        try:
            content = contract_path.read_text(encoding="utf-8")
            # ONEX_EXCLUDE: manual_yaml - validator contract loading requires raw YAML
            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                raise ModelOnexError(
                    message="Contract must be a YAML mapping",
                    error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                    context={
                        "validator_id": self.validator_id,
                        "contract_path": str(contract_path),
                    },
                )

            # Handle nested 'validation:' structure
            if "validation" in data and isinstance(data["validation"], dict):
                data = data["validation"]

            return ModelValidatorSubcontract.model_validate(data)

        except FILE_IO_ERRORS as e:
            # boundary-ok: convert file I/O errors to structured error
            raise ModelOnexError(
                message=f"Cannot read contract file: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "error": str(e),
                },
            ) from e
        except YAML_PARSING_ERRORS as e:
            # boundary-ok: convert YAML parsing errors to structured error
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {e}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "yaml_error": str(e),
                },
            ) from e

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for pattern violations.

        Uses AST analysis to detect pattern violations and returns
        issues for each violation found.

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            # File read error - skip silently (base class handles reporting)
            return ()

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Syntax error - skip silently (not a valid Python file for AST analysis)
            return ()

        # Run all pattern checkers
        checkers: list[ProtocolPatternChecker] = [
            PydanticPatternChecker(str(path)),
            NamingConventionChecker(str(path)),
            GenericPatternChecker(str(path)),
        ]

        all_issues: list[ModelValidationIssue] = []

        for checker in checkers:
            checker.visit(tree)
            for issue_str in checker.issues:
                line_number = _parse_line_number(issue_str)
                message = _parse_message(issue_str)
                rule_id = _categorize_issue(issue_str)

                # Get severity from contract rule, or use default
                severity = contract.severity_default
                for rule in contract.rules:
                    if rule.rule_id == rule_id and rule.enabled:
                        severity = rule.severity
                        break

                all_issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=message,
                        code=rule_id,
                        file_path=path,
                        line_number=line_number,
                        rule_name=rule_id,
                    )
                )

        return tuple(all_issues)


# =============================================================================
# Legacy API Functions
# =============================================================================


def validate_patterns_file(file_path: Path) -> list[str]:
    """Validate patterns in a Python file.

    Note: For new code, consider using ValidatorPatterns.validate_file() instead.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of issue strings in format "Line N: message".
    """
    all_issues: list[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        # Run all pattern checkers
        checkers: list[ProtocolPatternChecker] = [
            PydanticPatternChecker(str(file_path)),
            NamingConventionChecker(str(file_path)),
            GenericPatternChecker(str(file_path)),
        ]

        for checker in checkers:
            checker.visit(tree)
            all_issues.extend(checker.issues)

    except (SyntaxError, UnicodeDecodeError, ValueError) as e:
        all_issues.append(f"Error parsing {file_path}: {e}")

    return all_issues


def validate_patterns_directory(
    directory: Path,
    strict: bool = False,
) -> ModelValidationResult[None]:
    """Validate patterns in a directory.

    Note: For new code, consider using ValidatorPatterns.validate() instead.

    Args:
        directory: Directory to validate.
        strict: If True, validation fails on any issue found.

    Returns:
        ModelValidationResult with validation outcome.
    """
    python_files: list[Path] = []

    for py_file in directory.rglob("*.py"):
        # Skip excluded files
        if any(
            part in str(py_file)
            for part in [
                "__pycache__",
                ".git",
                "archived",
                "examples",
                "tests/fixtures",
            ]
        ):
            continue
        python_files.append(py_file)

    all_errors: list[str] = []
    files_with_errors: list[str] = []

    for py_file in python_files:
        issues = validate_patterns_file(py_file)
        if issues:
            files_with_errors.append(str(py_file))
            all_errors.extend([f"{py_file}: {issue}" for issue in issues])

    is_valid = len(all_errors) == 0 or not strict

    return ModelValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        metadata=ModelValidationMetadata(
            validation_type="patterns",
            files_processed=len(python_files),
            violations_found=len(all_errors),
            files_with_violations=files_with_errors,
            files_with_violations_count=len(files_with_errors),
            strict_mode=strict,
        ),
    )


def validate_patterns_cli() -> int:
    """CLI interface for pattern validation.

    Note: The main() method now uses ValidatorBase.main() instead.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate code patterns for ONEX compliance",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["src/"],
        help="Directories to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )

    args = parser.parse_args()

    print("ONEX Pattern Validation")
    print("=" * 40)

    overall_result: ModelValidationResult[None] = ModelValidationResult(
        is_valid=True,
        errors=[],
        metadata=ModelValidationMetadata(files_processed=0),
    )

    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory not found: {directory}")
            continue

        print(f"Scanning {directory}...")
        result = validate_patterns_directory(dir_path, args.strict)

        # Merge results
        overall_result.is_valid = overall_result.is_valid and result.is_valid
        overall_result.errors.extend(result.errors)
        if overall_result.metadata and result.metadata:
            overall_result.metadata.files_processed = (
                overall_result.metadata.files_processed or 0
            ) + (result.metadata.files_processed or 0)

        if result.errors:
            print(f"\nPattern issues found in {directory}:")
            for error in result.errors:
                print(f"   {error}")

    print("\nPattern Validation Summary:")
    files_processed = (
        overall_result.metadata.files_processed if overall_result.metadata else 0
    )
    print(f"   Files checked: {files_processed}")
    print(f"   Issues found: {len(overall_result.errors)}")

    if overall_result.is_valid:
        print("Pattern validation PASSED")
        return 0
    print("Pattern validation FAILED")
    return 1


# CLI entry point - uses new ValidatorBase.main() API
if __name__ == "__main__":
    sys.exit(ValidatorPatterns.main())


__all__ = [
    "GenericPatternChecker",
    "NamingConventionChecker",
    "ProtocolPatternChecker",
    "PydanticPatternChecker",
    "RULE_CLASS_ANTI_PATTERN",
    "RULE_CLASS_PASCAL_CASE",
    "RULE_ENTITY_NAME",
    "RULE_ENUM_FIELD",
    "RULE_FUNCTION_SNAKE_CASE",
    "RULE_GENERIC_FUNCTION",
    "RULE_GOD_CLASS",
    "RULE_MAX_PARAMS",
    "RULE_PYDANTIC_PREFIX",
    "RULE_UUID_FIELD",
    "ValidatorPatterns",
    "validate_patterns_cli",
    "validate_patterns_directory",
    "validate_patterns_file",
]
