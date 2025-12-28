"""Service for running validation suites.

This module provides a unified validation suite for ONEX compliance.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_validator_info import TypedDictValidatorInfo
from omnibase_core.validation.architecture import validate_architecture_directory
from omnibase_core.validation.contracts import validate_contracts_directory
from omnibase_core.validation.patterns import validate_patterns_directory
from omnibase_core.validation.types import validate_union_usage_directory
from omnibase_core.validation.validation_utils import ModelValidationResult


class ServiceValidationSuite:
    """Unified validation suite for ONEX compliance."""

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
            except Exception as e:
                # Create error result
                results[validation_type] = ModelValidationResult(
                    is_valid=False,
                    errors=[f"Validation failed: {e}"],
                    metadata=ModelValidationMetadata(
                        validation_type=validation_type,
                        files_processed=0,
                    ),
                )

        return results

    def list_validators(self) -> None:
        """List all available validators."""
        print("Available Validation Tools:")
        print("=" * 40)

        for name, info in self.validators.items():
            print(f"  {name:<15} - {info['description']}")

        print("\nUsage Examples:")
        print("  python -m omnibase_core.validation.cli architecture")
        print("  python -m omnibase_core.validation.cli union-usage --strict")
        print("  python -m omnibase_core.validation.cli all")
