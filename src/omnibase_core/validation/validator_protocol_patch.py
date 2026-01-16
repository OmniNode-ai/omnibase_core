"""
Protocol for Contract Patch Validators.

Defines the interface for validators that check contract patches
for structural and semantic correctness.

Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation

.. versionadded:: 0.4.0
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch

__all__ = [
    "ProtocolPatchValidator",
]


@runtime_checkable
class ProtocolPatchValidator(Protocol):
    """Protocol for contract patch validators.

    Defines the interface for validators that check contract patches
    for structural and semantic correctness.
    """

    def validate(self, patch: ModelContractPatch) -> ModelValidationResult[None]:
        """Validate a contract patch.

        Args:
            patch: The contract patch to validate.

        Returns:
            Validation result with is_valid flag and any issues found.
        """
        ...

    def validate_dict(
        self, data: dict[str, object]
    ) -> ModelValidationResult[ModelContractPatch]:
        """Validate a dictionary as a contract patch.

        Args:
            data: Dictionary representation of a contract patch.

        Returns:
            Validation result with parsed patch if valid.
        """
        ...

    def validate_file(self, path: Path) -> ModelValidationResult[ModelContractPatch]:
        """Validate a YAML file as a contract patch.

        Args:
            path: Path to the YAML file.

        Returns:
            Validation result with parsed patch if valid.
        """
        ...
