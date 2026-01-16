"""
Protocol for Constraint Validator (SPI Seam).

Defines the interface for constraint validators used in Phase 2 (MERGE) validation.
This protocol provides type safety for the duck-typed constraint validator seam
in ContractValidationPipeline, enabling future SPI integration.

Design Principles:
    - Protocol-first: Use typing.Protocol for interface definitions
    - Duck typing compatible: Existing implementations work without changes
    - Runtime checkable: Use @runtime_checkable for optional isinstance checks
    - SPI seam: Designed for future SPI constraint validator integration

Duck Typing Note:
    The ContractValidationPipeline accepts any object with a compatible
    `validate` method. This protocol documents the expected interface
    but does not enforce it at runtime. Implementations can be used
    without explicitly inheriting from this protocol.

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractValidationPipeline: Uses this protocol for constraint_validator
    - MergeValidator: Phase 2 validator that runs before constraint validator

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
    from omnibase_core.models.contracts.model_handler_contract import (
        ModelHandlerContract,
    )
    from omnibase_core.protocols.validation.protocol_constraint_validation_result import (
        ProtocolConstraintValidationResult,
    )


__all__ = [
    "ProtocolConstraintValidator",
]


@runtime_checkable
class ProtocolConstraintValidator(Protocol):
    """Protocol interface for constraint validators.

    Defines the interface for custom constraint validators that can be
    injected into ContractValidationPipeline for Phase 2 validation.
    This provides a typed seam for future SPI constraint validator integration.

    The validate method is called during merge validation with:
        - The base contract (from profile factory)
        - The patch that was applied
        - The resulting merged contract

    The result must have `is_valid`, `issues`, `errors`, and `warnings`
    attributes for proper integration with the pipeline.

    Example:
        >>> class MySPIConstraintValidator:
        ...     def validate(
        ...         self,
        ...         base: ModelHandlerContract,
        ...         patch: ModelContractPatch,
        ...         merged: ModelHandlerContract,
        ...     ) -> ProtocolConstraintValidationResult:
        ...         # Perform constraint validation
        ...         return MyValidationResult(is_valid=True)
        ...
        >>> pipeline = ContractValidationPipeline(
        ...     constraint_validator=MySPIConstraintValidator()
        ... )

    Thread Safety:
        Implementations should be stateless or thread-safe, as the pipeline
        may call validate() from multiple threads concurrently.

    See Also:
        - ProtocolConstraintValidationResult: Result interface
        - ContractValidationPipeline: Consumer of this protocol
        - MergeValidator: Runs before constraint validator
    """

    def validate(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
    ) -> ProtocolConstraintValidationResult:
        """Validate constraints on a merged contract.

        Called during Phase 2 (MERGE) validation to apply custom constraint
        checks beyond the standard MergeValidator checks.

        Args:
            base: The base contract from the profile factory.
            patch: The contract patch that was applied to the base.
            merged: The resulting merged contract to validate.

        Returns:
            A result object with the following attributes:
                - is_valid: True if constraints are satisfied
                - issues: List of validation issues found
                - errors: List of error messages
                - warnings: List of warning messages

        Raises:
            No exceptions should be raised. Return an invalid result
            with appropriate error messages instead.
        """
        ...
