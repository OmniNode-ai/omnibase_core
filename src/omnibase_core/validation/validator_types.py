"""
ValidatorUnionUsage - AST-based validator for Union type usage patterns.

This module provides the ValidatorUnionUsage class for analyzing Python source
code to detect Union type usage patterns that may violate ONEX type safety
standards.

The validator uses AST analysis to find:
- Unions with 3+ types that should be replaced with models
- Mixed primitive/complex type unions
- Primitive overload unions (str | int | bool | float)
- Overly broad "everything" unions
- Legacy Optional[T] syntax (should use T | None)
- Legacy Union[T, None] syntax (should use T | None)

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorUnionUsage

        validator = ValidatorUnionUsage()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_types src/

    Legacy function usage::

        from omnibase_core.validation.validator_types import validate_union_usage_file

        union_count, issues, patterns = validate_union_usage_file(Path("src/module.py"))

Thread Safety:
    ValidatorUnionUsage instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - UnionUsageChecker: AST visitor that detects union patterns
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, YAML_PARSING_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern
from omnibase_core.validation.checker_union_usage import UnionUsageChecker
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_utils import ModelValidationResult


class ValidatorUnionUsage(ValidatorBase):
    """Validator for detecting Union type usage patterns in Python code.

    This validator uses AST analysis to detect potentially problematic uses
    of Union types, including:
    - Unions with 3+ types (complexity indicator)
    - Mixed primitive/complex type unions
    - Primitive overload (4+ primitive types in union)
    - Overly broad "everything" unions
    - Legacy Optional[T] syntax (prefer T | None)
    - Legacy Union[T, None] syntax (prefer T | None)

    The validator respects exemptions via:
    - Inline suppression comments from contract configuration

    Attributes:
        validator_id: Unique identifier for this validator ("union_usage").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_types import ValidatorUnionUsage
        >>> validator = ValidatorUnionUsage()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "union_usage"

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
        """Validate a single Python file for Union type usage.

        Uses AST analysis to detect Union type patterns and returns
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

        # Create checker and visit the AST
        checker = UnionUsageChecker(str(path))
        checker.visit(tree)

        # Convert checker issues to ModelValidationIssue
        issues: list[ModelValidationIssue] = []

        for issue_str in checker.issues:
            # Parse line number from issue string (format: "Line N: message")
            line_number = self._extract_line_number(issue_str)
            severity = self._determine_severity(issue_str, contract)
            rule_name = self._determine_rule_name(issue_str)

            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=issue_str,
                    file_path=path,
                    line_number=line_number,
                    rule_name=rule_name,
                )
            )

        return tuple(issues)

    def _extract_line_number(self, issue_str: str) -> int | None:
        """Extract line number from issue string.

        Args:
            issue_str: Issue string in format "Line N: message".

        Returns:
            Line number if found, None otherwise.
        """
        # Pattern: "Line N:" at the start
        match = re.match(r"Line (\d+):", issue_str)
        if match:
            return int(match.group(1))
        return None

    def _determine_severity(
        self,
        issue_str: str,
        contract: ModelValidatorSubcontract,
    ) -> EnumValidationSeverity:
        """Determine severity for an issue based on contract rules.

        Args:
            issue_str: The issue message string.
            contract: Validator contract with rule configurations.

        Returns:
            Appropriate severity level based on issue type and contract.
        """
        # Map issue patterns to rule IDs
        rule_id = self._determine_rule_name(issue_str)

        # Find matching rule in contract
        if rule_id:
            for rule in contract.rules:
                if rule.rule_id == rule_id and rule.enabled:
                    return rule.severity

        return contract.severity_default

    def _determine_rule_name(self, issue_str: str) -> str | None:
        """Determine the rule name from the issue string.

        Args:
            issue_str: The issue message string.

        Returns:
            Rule ID if pattern matches, None otherwise.
        """
        lower_issue = issue_str.lower()

        if "4+ primitive types" in lower_issue or "primitive_overload" in lower_issue:
            return "primitive_overload"
        if "mixed primitive/complex" in lower_issue:
            return "mixed_primitive_complex"
        if "overly broad" in lower_issue:
            return "everything_union"
        if "optional[" in lower_issue and "instead of" in lower_issue:
            return "optional_syntax"
        if "union[" in lower_issue and ", none]" in lower_issue:
            return "union_none_syntax"
        if "3+" in lower_issue or "complex" in lower_issue:
            return "complex_union"

        return None


# =============================================================================
# Legacy API Functions
# =============================================================================


def validate_union_usage_file(
    file_path: Path,
) -> tuple[int, list[str], list[ModelUnionPattern]]:
    """Validate Union usage in a Python file.

    Note: For new code, consider using ValidatorUnionUsage.validate_file() instead.

    Returns a tuple of (union_count, issues, patterns).
    Errors are returned as issues in the list, not raised.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker(str(file_path))
        checker.visit(tree)

        return checker.union_count, checker.issues, checker.union_patterns

    except FileNotFoundError as e:
        # Return file not found error as an issue
        return 0, [f"Error: File not found: {e}"], []
    except SyntaxError as e:
        # Return syntax error as an issue
        return 0, [f"Error parsing {file_path}: {e}"], []
    except (
        Exception
    ) as e:  # fallback-ok: Validation errors are returned as issues, not raised
        # Return other errors as issues
        return 0, [f"Failed to validate union usage in {file_path}: {e}"], []


def validate_union_usage_directory(
    directory: Path, max_unions: int = 100, strict: bool = False
) -> ModelValidationResult[None]:
    """Validate Union usage in a directory.

    Note: For new code, consider using ValidatorUnionUsage.validate() instead.
    """
    python_files = []
    for py_file in directory.rglob("*.py"):
        # Filter out archived files, examples, and __pycache__
        if any(
            part in str(py_file)
            for part in [
                "/archived/",
                "archived",
                "/archive/",
                "archive",
                "/examples/",
                "examples",
                "__pycache__",
            ]
        ):
            continue
        python_files.append(py_file)

    if not python_files:
        return ModelValidationResult(
            is_valid=True,
            errors=[],
            metadata=ModelValidationMetadata(
                files_processed=0,
            ),
        )

    total_unions = 0
    total_issues = []
    all_patterns = []

    # Process all files
    for py_file in python_files:
        union_count, issues, patterns = validate_union_usage_file(py_file)
        total_unions += union_count
        all_patterns.extend(patterns)

        if issues:
            total_issues.extend([f"{py_file}: {issue}" for issue in issues])

    is_valid = (total_unions <= max_unions) and (not total_issues or not strict)

    return ModelValidationResult(
        is_valid=is_valid,
        errors=total_issues,
        metadata=ModelValidationMetadata(
            validation_type="union_usage",
            files_processed=len(python_files),
            violations_found=len(total_issues),
            total_unions=total_unions,
            max_unions=max_unions,
            complex_patterns=len([p for p in all_patterns if p.type_count >= 3]),
            strict_mode=strict,
        ),
    )


def validate_union_usage_cli() -> int:
    """CLI interface for union usage validation.

    Note: For new code, consider running the module directly:
        python -m omnibase_core.validation.validator_types src/
    """
    parser = argparse.ArgumentParser(
        description="Enhanced Union type usage validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool detects complex Union types that should be replaced with proper models:

* Unions with 3+ types that could be models
* Repeated union patterns across files
* Mixed primitive/complex type unions
* Overly broad unions that should use specific types, generics, or strongly-typed models

Examples of problematic patterns:
* Union[str, int, bool, float] -> Use specific type (str), generic TypeVar, or domain-specific model
* Union[str, int, dict[str, Any]] -> Use specific type or generic TypeVar
* Union[dict[str, Any], list[Any], str] -> Use specific collection type or generic
        """,
    )
    parser.add_argument(
        "--max-unions", type=int, default=100, help="Maximum allowed Union types"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation mode"
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    if base_path.is_file() and base_path.suffix == ".py":
        # Single file validation
        union_count, issues, _ = validate_union_usage_file(base_path)

        if issues:
            print(f"Union validation issues found in {base_path}:")
            for issue in issues:
                print(f"   {issue}")
            return 1

        print(
            f"Union validation: {union_count} unions in {base_path} (limit: {args.max_unions})"
        )
        return 0
    # Directory validation
    result = validate_union_usage_directory(base_path, args.max_unions, args.strict)

    if result.errors:
        print("Union validation issues found:")
        for error in result.errors:
            print(f"   {error}")

    total_unions = (
        result.metadata.total_unions
        if result.metadata and result.metadata.total_unions is not None
        else 0
    )
    if total_unions > args.max_unions:
        print(f"Union count exceeded: {total_unions} > {args.max_unions}")
        return 1

    if result.errors:
        return 1

    total_unions_final = (
        result.metadata.total_unions
        if result.metadata and result.metadata.total_unions is not None
        else 0
    )
    files_processed = (
        result.metadata.files_processed
        if result.metadata and result.metadata.files_processed is not None
        else 0
    )
    print(f"Union validation: {total_unions_final} unions in {files_processed} files")
    return 0


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorUnionUsage.main())


__all__ = [
    # New ValidatorBase-based class
    "ValidatorUnionUsage",
    # Legacy API exports
    "validate_union_usage_cli",
    "validate_union_usage_directory",
    "validate_union_usage_file",
]
