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
import logging
import re
import sys
from pathlib import Path
from typing import ClassVar, Protocol

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_utils import ModelValidationResult

from .checker_generic_pattern import GenericPatternChecker
from .checker_naming_convention import NamingConventionChecker
from .checker_pydantic_pattern import PydanticPatternChecker

# Configure logger for this module
logger = logging.getLogger(__name__)

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
RULE_UNKNOWN: str = "unknown"

# Compiled regex patterns for issue categorization
# Patterns use anchored phrases from actual checker output messages for precise matching.
# Order matters: more specific patterns should come before generic ones.
#
# Pattern Design Principles:
# 1. Match exact phrases from checker output (see checker_*.py files)
# 2. All patterns MUST be fully anchored with ^ and $ for precise matching
# 3. Use case-insensitive matching for robustness where appropriate
# 4. More specific patterns BEFORE generic ones (e.g., "Async function" before "Function")
#
# IMPORTANT: All patterns use full anchoring (^ and $) to prevent partial matches.
# The .* captures variable content like names and counts. Without $ anchors,
# patterns could match unintended messages leading to misclassification.
#
# If a pattern fails to match, the issue falls back to RULE_UNKNOWN which defaults
# to enabled. Keep patterns synchronized with checker output to prevent miscategorization.
_ISSUE_CATEGORY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Pydantic pattern checks - match exact phrases from PydanticPatternChecker
    # Message: "Pydantic model '{name}' should start with 'Model'"
    (
        re.compile(r"^Pydantic model '.*' should start with 'Model'$"),
        RULE_PYDANTIC_PREFIX,
    ),
    # Message: "Field '{name}' should use UUID type instead of str"
    (re.compile(r"^Field '.*' should use UUID type instead of str$"), RULE_UUID_FIELD),
    # Message: "Field '{name}' should use Enum instead of str"
    (re.compile(r"^Field '.*' should use Enum instead of str$"), RULE_ENUM_FIELD),
    # Message: "Field '{name}' might reference an entity - consider using ID + display_name pattern"
    (
        re.compile(
            r"^Field '.*' might reference an entity - consider using ID \+ display_name pattern$"
        ),
        RULE_ENTITY_NAME,
    ),
    # Generic pattern checks - match exact phrases from GenericPatternChecker
    # Message: "Function name '{name}' is too generic - use specific domain terminology"
    (
        re.compile(
            r"^Function name '.*' is too generic - use specific domain terminology$"
        ),
        RULE_GENERIC_FUNCTION,
    ),
    # Message: "Function '{name}' has {count} parameters - consider using a model or breaking into smaller functions"
    (
        re.compile(
            r"^Function '.*' has \d+ parameters - consider using a model or breaking into smaller functions$"
        ),
        RULE_MAX_PARAMS,
    ),
    # Message: "Class '{name}' has {count} methods - consider breaking into smaller classes"
    (
        re.compile(
            r"^Class '.*' has \d+ methods - consider breaking into smaller classes$"
        ),
        RULE_GOD_CLASS,
    ),
    # Naming convention checks - match exact phrases from NamingConventionChecker
    # Message: "Class name '{name}' contains anti-pattern '{pattern}' - use specific domain terminology"
    (
        re.compile(
            r"^Class name '.*' contains anti-pattern '.*' - use specific domain terminology$"
        ),
        RULE_CLASS_ANTI_PATTERN,
    ),
    # Message: "Class name '{name}' should use PascalCase"
    (re.compile(r"^Class name '.*' should use PascalCase$"), RULE_CLASS_PASCAL_CASE),
    # Message: "Async function name '{name}' should use snake_case" (check async first - more specific)
    (
        re.compile(r"^Async function name '.*' should use snake_case$"),
        RULE_FUNCTION_SNAKE_CASE,
    ),
    # Message: "Function name '{name}' should use snake_case"
    (
        re.compile(r"^Function name '.*' should use snake_case$"),
        RULE_FUNCTION_SNAKE_CASE,
    ),
)


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
    match = re.match(r"^Line (\d+):", issue)
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
    match = re.match(r"^Line \d+: (.*)", issue)
    if match:
        return match.group(1)
    return issue


def _categorize_issue(issue: str) -> str:
    """Categorize an issue string to a rule ID using compiled regex patterns.

    Uses pre-compiled regex patterns with full anchoring (^ and $) for
    precise matching. Patterns are checked in order, with more specific
    patterns before generic ones.

    Implementation Notes:
        - Uses ``fullmatch()`` for fully-anchored patterns (^ and $) to ensure
          exact string matching and avoid partial match misclassification.
        - If a pattern fails to match, the issue falls back to RULE_UNKNOWN.
        - Keep patterns synchronized with checker output to prevent miscategorization.

    Args:
        issue: The issue message to categorize (without "Line N:" prefix).

    Returns:
        The rule ID corresponding to the issue type, or RULE_UNKNOWN if
        no pattern matches (with a debug log).
    """
    for pattern, rule_id in _ISSUE_CATEGORY_PATTERNS:
        if pattern.fullmatch(issue):
            return rule_id

    # Log uncategorized issues for debugging - helps identify missing patterns
    logger.debug("Could not categorize issue to a rule: %s", issue[:100])
    return RULE_UNKNOWN


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

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorPatterns instances are NOT thread-safe due to internal mutable
        state. Specifically:

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
        except OSError as e:
            # fallback-ok: log warning and skip file on read errors
            logger.warning("Cannot read file %s: %s", path, e)
            return ()

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            # fallback-ok: log warning and skip file with syntax errors
            logger.warning(
                "Skipping file with syntax error: path=%s, line=%s, error=%s",
                path,
                e.lineno,
                e.msg,
            )
            return ()

        # Precompute rule configuration cache for O(1) lookups during issue processing.
        # This is done once per validator instance (on first file), then reused.
        # The cache maps rule_id -> (enabled, severity) for fast filtering.
        if self._rule_config_cache is None:
            self._rule_config_cache = self._build_rule_config_cache(contract)

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
                # Categorize using the extracted message (without "Line N:" prefix)
                # to match anchored regex patterns correctly
                rule_id = _categorize_issue(message)

                # Check if rule is enabled before adding issue (O(1) cache lookup)
                enabled, severity = self._get_rule_config(rule_id, contract)
                if not enabled:
                    # Rule is explicitly disabled in contract, skip this issue
                    logger.debug(
                        "Skipping issue for disabled rule %s: %s",
                        rule_id,
                        message[:50],
                    )
                    continue

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
# Standalone API Functions
# =============================================================================


def validate_patterns_file(file_path: Path) -> list[str]:
    """Validate patterns in a Python file.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of issue strings in format "Line N: message".

    See Also:
        ValidatorPatterns.validate_file(): Class-based validation with contracts.
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

    except OSError as e:
        # fallback-ok: log file read errors for debugging
        logger.warning("Cannot read file %s: %s", file_path, e)
        all_issues.append(f"Error reading {file_path}: {e}")
    except (SyntaxError, UnicodeDecodeError, ValueError) as e:
        # fallback-ok: log parsing errors for debugging
        logger.debug("Error parsing %s: %s", file_path, e)
        all_issues.append(f"Error parsing {file_path}: {e}")

    return all_issues


def validate_patterns_directory(
    directory: Path,
    strict: bool = False,
) -> ModelValidationResult[None]:
    """Validate patterns in a directory.

    Args:
        directory: Directory to validate.
        strict: If True, validation fails on any issue found.

    Returns:
        ModelValidationResult with validation outcome.

    See Also:
        ValidatorPatterns.validate(): Class-based validation with contracts.
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
    "RULE_UNKNOWN",
    "RULE_UUID_FIELD",
    "ValidatorPatterns",
    "validate_patterns_cli",
    "validate_patterns_directory",
    "validate_patterns_file",
]
