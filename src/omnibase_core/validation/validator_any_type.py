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

import yaml

# Configure logger for this module
logger = logging.getLogger(__name__)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, YAML_PARSING_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.visitor_any_type import (
    EXEMPT_DECORATORS,
    RULE_ANY_ANNOTATION,
    RULE_ANY_IMPORT,
    RULE_DICT_STR_ANY,
    RULE_LIST_ANY,
    RULE_UNION_WITH_ANY,
    AnyTypeVisitor,
)


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
        """Validate a single Python file for Any type usage.

        Uses AST analysis to detect Any type patterns and returns
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
        except SyntaxError:
            # Syntax error - skip silently (not a valid Python file for AST analysis)
            return ()

        lines = source.splitlines()

        # Create visitor with contract configuration
        visitor = AnyTypeVisitor(
            source_lines=lines,
            suppression_patterns=contract.suppression_comments,
            file_path=path,
            severity=contract.severity_default,
        )

        # Visit the AST
        visitor.visit(tree)

        return tuple(visitor.issues)


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
