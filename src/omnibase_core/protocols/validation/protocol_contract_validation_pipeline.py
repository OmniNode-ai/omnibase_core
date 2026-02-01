"""
Protocol for Contract Validation Pipeline.

Defines the interface that pipeline implementations must follow.
This protocol enables duck typing for custom pipeline implementations
and provides clear documentation of the expected interface.

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractValidationPipeline: Default implementation
    - ModelExpandedContractResult: Result model

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.common.model_validation_result import (
        ModelValidationResult,
    )
    from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
    from omnibase_core.models.contracts.model_handler_contract import (
        ModelHandlerContract,
    )
    from omnibase_core.models.validation.model_expanded_contract_result import (
        ModelExpandedContractResult,
    )

__all__ = [
    "ProtocolContractValidationPipeline",
]


@runtime_checkable
class ProtocolContractValidationPipeline(Protocol):
    """Protocol interface for contract validation pipelines.

    Defines the interface that pipeline implementations must follow.
    This protocol enables duck typing for custom pipeline implementations
    and provides clear documentation of the expected interface.

    Methods:
        validate_patch: Validate a contract patch (Phase 1)
        validate_merge: Validate a merge result (Phase 2)
        validate_expanded: Validate an expanded contract (Phase 3)
        validate_all: Run all phases and return expanded contract
    """

    def validate_patch(self, patch: ModelContractPatch) -> ModelValidationResult[None]:
        """Validate a contract patch before merge (Phase 1).

        Args:
            patch: The contract patch to validate.

        Returns:
            Validation result with issues found during patch validation.
        """
        ...

    def validate_merge(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
    ) -> ModelValidationResult[None]:
        """Validate a merge result before expansion (Phase 2).

        Args:
            base: The base contract from profile factory.
            patch: The patch that was applied.
            merged: The resulting merged contract.

        Returns:
            Validation result with issues found during merge validation.
        """
        ...

    def validate_expanded(
        self,
        contract: ModelHandlerContract,
    ) -> ModelValidationResult[None]:
        """Validate a fully expanded contract for runtime (Phase 3).

        Args:
            contract: The fully expanded contract to validate.

        Returns:
            Validation result with issues found during expanded validation.
        """
        ...

    def validate_all(
        self,
        patch: ModelContractPatch,
        profile_factory: object,
    ) -> ModelExpandedContractResult:
        """Run all validation phases and return expanded contract.

        Args:
            patch: The contract patch to validate and expand.
            profile_factory: Factory for resolving base contracts from profiles.

        Returns:
            ModelExpandedContractResult with the validated contract or errors.
        """
        ...
