"""Service for running validation suites.

This module provides a unified validation suite for ONEX compliance.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_validator_info import TypedDictValidatorInfo
from omnibase_core.validation.validator_architecture import (
    validate_architecture_directory,
)
from omnibase_core.validation.validator_contracts import validate_contracts_directory
from omnibase_core.validation.validator_patterns import validate_patterns_directory
from omnibase_core.validation.validator_types import validate_union_usage_directory
from omnibase_core.validation.validator_utils import ModelValidationResult


class ServiceValidationSuite:
    """
    Unified validation suite for ONEX compliance.

    Provides a centralized registry of validation tools for checking
    ONEX architectural patterns, type usage, contracts, and code
    conventions. Supports running individual validations or all
    validations at once on a directory.

    Available Validators:
        - architecture: Validate ONEX one-model-per-file architecture
        - union-usage: Validate Union type usage patterns
        - contracts: Validate YAML contract files
        - patterns: Validate code patterns and conventions

    Example:
        >>> from omnibase_core.services import ServiceValidationSuite
        >>> suite = ServiceValidationSuite()
        >>> result = suite.run_validation("architecture", Path("src/"))
        >>> print(result.is_valid)

    Thread Safety:
        This class is thread-safe for concurrent read operations. The internal
        validators dictionary is populated once during __init__ and is never
        modified thereafter. All validation methods create fresh result objects
        and do not mutate instance state. Multiple threads can safely call
        run_validation() and run_all_validations() concurrently on the same
        instance. See docs/guides/THREADING.md for more details.

    .. note::
        Previously named ``ModelValidationSuite``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Service``
        prefix indicates a stateful service class.
    """

    def __init__(self) -> None:
        self.validators: dict[str, TypedDictValidatorInfo] = {
            "architecture": {
                "func": validate_architecture_directory,
                "description": "Validate ONEX one-model-per-file architecture",
                "args": ["max_violations"],
            },
            "union-usage": {
                "func": validate_union_usage_directory,
                "description": "Validate Union type usage patterns",
                "args": ["max_unions", "strict"],
            },
            "contracts": {
                "func": validate_contracts_directory,
                "description": "Validate YAML contract files",
                "args": [],
            },
            "patterns": {
                "func": validate_patterns_directory,
                "description": "Validate code patterns and conventions",
                "args": ["strict"],
            },
        }

    @standard_error_handling("Validation execution")
    def run_validation(
        self,
        validation_type: str,
        directory: Path,
        **kwargs: object,
    ) -> ModelValidationResult[None]:
        """Run a specific validation on a directory."""
        if validation_type not in self.validators:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown validation type: {validation_type}",
            )

        validator_info = self.validators[validation_type]
        validator_func = validator_info["func"]

        # Filter kwargs to only include relevant parameters
        relevant_args: list[str] = validator_info["args"]
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in relevant_args}

        # Direct call since validator_func is properly typed through ValidatorInfo
        return validator_func(directory, **filtered_kwargs)

    def run_all_validations(
        self,
        directory: Path,
        **kwargs: object,
    ) -> dict[str, ModelValidationResult[None]]:
        """Run all validations on a directory."""
        results = {}

        for validation_type in self.validators:
            try:
                result = self.run_validation(validation_type, directory, **kwargs)
                results[validation_type] = result
            except ModelOnexError as e:
                # fallback-ok: capture ONEX framework errors as validation failures
                results[validation_type] = ModelValidationResult(
                    is_valid=False,
                    errors=[f"Validation error: {e.message}"],
                    metadata=ModelValidationMetadata(
                        validation_type=validation_type,
                        files_processed=0,
                    ),
                )
            except OSError as e:
                # fallback-ok: capture file system errors as validation failures
                results[validation_type] = ModelValidationResult(
                    is_valid=False,
                    errors=[f"File system error: {e}"],
                    metadata=ModelValidationMetadata(
                        validation_type=validation_type,
                        files_processed=0,
                    ),
                )
            except (TypeError, ValueError) as e:
                # fallback-ok: capture data validation errors as validation failures
                results[validation_type] = ModelValidationResult(
                    is_valid=False,
                    errors=[f"Validation failed: {e}"],
                    metadata=ModelValidationMetadata(
                        validation_type=validation_type,
                        files_processed=0,
                    ),
                )

        return results

    def get_validators(self) -> dict[str, str]:
        """Return available validators and their descriptions.

        Returns a dictionary mapping validator names to their descriptions.
        This method is preferable for programmatic usage as it returns
        structured data that can be formatted as needed.

        Returns:
            dict[str, str]: Mapping of validator names to descriptions.

        Example:
            >>> suite = ServiceValidationSuite()
            >>> validators = suite.get_validators()
            >>> for name, desc in validators.items():
            ...     print(f"{name}: {desc}")
        """
        return {name: info["description"] for name, info in self.validators.items()}

    def list_validators(self) -> None:
        """List all available validators (CLI output).

        Prints formatted output suitable for CLI usage. For programmatic
        access, use :meth:`get_validators` instead which returns a dict.
        """
        print("Available Validation Tools:")  # print-ok: CLI user output
        print("=" * 40)  # print-ok: CLI user output

        for name, description in self.get_validators().items():
            print(f"  {name:<15} - {description}")  # print-ok: CLI user output

        print("\nUsage Examples:")  # print-ok: CLI user output
        print(
            "  python -m omnibase_core.validation.cli architecture"
        )  # print-ok: CLI user output
        print(
            "  python -m omnibase_core.validation.cli union-usage --strict"
        )  # print-ok: CLI user output
        print(
            "  python -m omnibase_core.validation.cli all"
        )  # print-ok: CLI user output
