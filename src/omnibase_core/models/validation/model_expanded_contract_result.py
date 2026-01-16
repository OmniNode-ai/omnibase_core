"""
Expanded Contract Result Model.

Result of the full contract validation pipeline (PATCH -> MERGE -> EXPANDED).

This model captures the outcome of running all three validation phases
and includes the resulting contract if successful.

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractValidationPipeline: Pipeline that produces this result
    - EnumValidationPhase: Pipeline phase enumeration

.. versionadded:: 0.4.1
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract

__all__ = [
    "ModelExpandedContractResult",
]


class ModelExpandedContractResult(BaseModel):
    """Result of the full contract validation pipeline.

    This model captures the outcome of running all three validation phases
    (PATCH, MERGE, EXPANDED) and includes the resulting contract if successful.

    The result provides:
    - Overall success/failure status
    - The expanded contract (if all phases passed)
    - Validation results for each phase that was executed
    - Aggregated error messages
    - The phase where validation failed (if applicable)

    Attributes:
        success: Overall pipeline success status. True only if all executed
            phases passed validation.
        contract: The fully expanded and validated contract. Only populated
            if success is True. None if any phase failed.
        validation_results: Validation results keyed by phase name. Contains
            results for each phase that was executed (may not include all
            phases if an early phase failed).
        errors: Aggregated error messages from all phases. Useful for
            displaying a summary of all issues found.
        phase_failed: The phase where validation first failed, if any.
            None if all phases passed.

    Example:
        >>> result = pipeline.validate_all(patch, factory)
        >>> if result.success:
        ...     contract = result.contract
        ...     print(f"Validated: {contract.name}")
        ... else:
        ...     print(f"Failed at phase: {result.phase_failed}")
        ...     for error in result.errors:
        ...         print(f"  - {error}")
    """

    # frozen=False: This result is built incrementally during pipeline execution.
    # Fields like validation_results and errors are populated as phases complete.
    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    success: bool = Field(
        default=False,
        description="Overall pipeline success status",
    )
    contract: ModelHandlerContract | None = Field(
        default=None,
        description="The expanded contract (only if success=True)",
    )
    validation_results: dict[str, ModelValidationResult[None]] = Field(
        default_factory=dict,
        description="Validation results by phase name",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Aggregated error messages from all phases",
    )
    phase_failed: EnumValidationPhase | None = Field(
        default=None,
        description="The phase where validation failed (if any)",
    )
