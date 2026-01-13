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
- Optional[T] syntax (should use T | None per PEP 604)
- Union[T, None] syntax (should use T | None per PEP 604)

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

    Standalone function usage::

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
import logging
import re
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.errors.exception_groups import FILE_IO_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern
from omnibase_core.validation.checker_union_usage import UnionUsageChecker
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_utils import ModelValidationResult

# Configure logger for this module
logger = logging.getLogger(__name__)


class ValidatorUnionUsage(ValidatorBase):
    """Validator for detecting Union type usage patterns in Python code.

    This validator uses AST analysis to detect potentially problematic uses
    of Union types, including:
    - Unions with 3+ types (complexity indicator)
    - Mixed primitive/complex type unions
    - Primitive overload (4+ primitive types in union)
    - Overly broad "everything" unions
    - Optional[T] syntax (prefer T | None per PEP 604)
    - Union[T, None] syntax (prefer T | None per PEP 604)

    The validator respects exemptions via:
    - Inline suppression comments from contract configuration

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorUnionUsage instances are NOT thread-safe due to internal
        mutable state. Specifically:

        - ``_file_line_cache`` (inherited from ValidatorBase): Caches file
          contents during validation. Concurrent access from multiple threads
          could cause cache corruption or stale reads.

        - ``_rule_config_cache``: Lazily built dictionary mapping rule IDs to
          configurations. While the lazy initialization is mostly safe due to
          Python's GIL, concurrent first-access from multiple threads could
          cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**

        The contract (ModelValidatorSubcontract) is immutable (frozen=True)
        and safe to share across threads.

        For more details, see the Threading Guide:
        ``docs/guides/THREADING.md``

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

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for Union type usage.

        Uses AST analysis to detect Union type patterns and returns
        issues for each violation found.

        Note:
            A fresh UnionUsageChecker instance is created for each file,
            ensuring clean AST visitor state between files. This prevents
            state leakage (e.g., _in_union_binop flag) across file boundaries.

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except FILE_IO_ERRORS as e:
            # fallback-ok: log warning and skip file on read errors
            logger.warning(
                "Cannot read file for union validation: path=%s, error_type=%s, error=%s",
                path,
                type(e).__name__,
                e,
            )
            return ()

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            # fallback-ok: log warning and skip file with syntax errors
            logger.warning(
                "Skipping file with syntax error during AST parsing: "
                "path=%s, line=%s, error=%s",
                path,
                e.lineno,
                e.msg,
            )
            return ()

        # Create fresh checker instance for this file (ensures clean visitor state)
        checker = UnionUsageChecker(str(path))
        checker.visit(tree)

        # Convert checker issues to ModelValidationIssue
        issues: list[ModelValidationIssue] = []

        for issue_str in checker.issues:
            # Parse line number from issue string (format: "Line N: message")
            line_number = self._extract_line_number(issue_str)
            rule_name = self._determine_rule_name(issue_str)

            # Check if rule is enabled before adding issue
            enabled, severity = self._get_rule_config(rule_name, contract)
            if not enabled:
                # Rule is explicitly disabled in contract, skip this issue
                continue

            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=issue_str,
                    code=rule_name,
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

    def _determine_rule_name(self, issue_str: str) -> str:
        """Determine the rule name from the issue string.

        Args:
            issue_str: The issue message string.

        Returns:
            Rule ID matching the issue pattern. Returns "unknown_union_pattern"
            as fallback if no specific pattern matches, ensuring all
            ModelValidationIssue instances have a valid code for programmatic
            handling.
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

        # Fallback: Always return a valid code for programmatic handling
        return "unknown_union_pattern"


# =============================================================================
# Standalone API Functions
# =============================================================================


def validate_union_usage_file(
    file_path: Path,
) -> tuple[int, list[str], list[ModelUnionPattern]]:
    """Validate Union usage in a Python file.

    Returns a tuple of (union_count, issues, patterns).
    Errors are returned as issues in the list, not raised.

    See Also:
        ValidatorUnionUsage.validate_file(): Class-based validation with contracts.
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

    See Also:
        ValidatorUnionUsage.validate(): Class-based validation with contracts.
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

    See Also:
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
    # ValidatorBase-based class
    "ValidatorUnionUsage",
    # Standalone function exports
    "validate_union_usage_cli",
    "validate_union_usage_directory",
    "validate_union_usage_file",
]
