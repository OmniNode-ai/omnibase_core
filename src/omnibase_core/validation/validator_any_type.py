"""
ValidatorAnyType - AST-based validator for Any type usage patterns.

This module provides the ValidatorAnyType class for analyzing Python source
code to detect Any type usage patterns that may violate ONEX type safety
standards.

The validator uses AST analysis to find:
- `from typing import Any` imports
- `Any` in type annotations (param: Any, -> Any)
- `dict[str, Any]` patterns
- `list[Any]` patterns
- `Union[..., Any]` or `X | Any` patterns

Exemptions are respected via:
- @allow_any_type decorator on function/class
- @allow_dict_any decorator on function/class
- Inline suppression comments from contract configuration

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorAnyType

        validator = ValidatorAnyType()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_any_type src/

Thread Safety:
    ValidatorAnyType instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - decorator_allow_any_type: Decorator for exempting functions from Any checks
    - decorator_allow_dict_any: Decorator for exempting dict[str, Any] usage
"""

import ast
import logging
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_visitor_any_type import (
    EXEMPT_DECORATORS,
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
    AnyTypeVisitor,
)
from omnibase_core.validation.validator_base import ValidatorBase

# Configure logger for this module
logger = logging.getLogger(__name__)


class ValidatorAnyType(ValidatorBase):
    """Validator for detecting Any type usage patterns in Python code.

    This validator uses AST analysis to detect potentially problematic uses
    of the Any type, including:
    - Direct imports of Any from typing
    - Any in function parameters or return types
    - dict[str, Any] patterns (prefer TypedDict or Pydantic models)
    - list[Any] patterns (prefer specific element types)
    - Union[..., Any] patterns (defeats type checking)

    The validator respects exemptions via:
    - @allow_any_type decorator
    - @allow_dict_any decorator
    - Inline suppression comments

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorAnyType instances are NOT thread-safe due to internal mutable
        state inherited from ValidatorBase. Specifically:

        - ``_file_line_cache`` (inherited from ValidatorBase): Caches file
          contents during validation. Concurrent access from multiple threads
          could cause cache corruption or stale reads.

        - ``_rule_config_cache`` (inherited from ValidatorBase): Lazily built
          dictionary mapping rule IDs to configurations. While the lazy
          initialization is mostly safe due to Python's GIL, concurrent
          first-access from multiple threads could cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**

        The contract (ModelValidatorSubcontract) is immutable (frozen=True)
        and safe to share across threads.

        For more details, see the Threading Guide:
        ``docs/guides/THREADING.md``

    Attributes:
        validator_id: Unique identifier for this validator ("any_type").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_any_type import ValidatorAnyType
        >>> validator = ValidatorAnyType()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "any_type"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for Any type usage.

        Uses AST analysis to detect Any type patterns and returns
        issues for each violation found. Applies per-rule enablement
        and severity overrides from the contract.

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

        lines = source.splitlines()

        # Create visitor with contract configuration
        # We use default severity here; per-rule overrides are applied below
        visitor = AnyTypeVisitor(
            source_lines=lines,
            suppression_patterns=contract.suppression_comments,
            file_path=path,
            severity=contract.severity_default,
        )

        # Visit the AST
        visitor.visit(tree)

        # Apply per-rule enablement and severity overrides from contract
        filtered_issues: list[ModelValidationIssue] = []
        for issue in visitor.issues:
            # Get rule configuration (use code as rule_id)
            rule_id = issue.code if issue.code else "unknown"
            enabled, severity = self._get_rule_config(rule_id, contract)

            # Skip disabled rules
            if not enabled:
                continue

            # Apply per-rule severity override if different from default
            if severity != issue.severity:
                # Create new issue with overridden severity
                issue = ModelValidationIssue(
                    severity=severity,
                    message=issue.message,
                    code=issue.code,
                    file_path=issue.file_path,
                    line_number=issue.line_number,
                    rule_name=issue.rule_name,
                    suggestion=issue.suggestion,
                )

            filtered_issues.append(issue)

        return tuple(filtered_issues)


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorAnyType.main())


__all__ = [
    "AnyTypeVisitor",
    "EXEMPT_DECORATORS",
    "RULE_ANY_ANNOTATION",
    "RULE_ANY_IMPORT",
    "RULE_DICT_STR_ANY",
    "RULE_LIST_ANY",
    "RULE_UNION_WITH_ANY",
    "ValidatorAnyType",
]
