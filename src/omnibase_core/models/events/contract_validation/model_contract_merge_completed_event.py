"""
Contract merge completed event model.

This module provides the event model for when contract merge operations complete.
This event contains information about the resulting effective contract.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_merge_completed_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractMergeCompletedEvent,
        )

Event Type:
    ``onex.contract.merge.completed``

See Also:
    - :class:`ModelContractMergeStartedEvent`: Emitted when merge starts

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1146 contract validation events.
"""

from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.models.events.contract_validation.model_contract_ref import (
    ModelContractRef,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_event_base import (
    ModelContractValidationEventBase,
)

__all__ = ["ModelContractMergeCompletedEvent", "CONTRACT_MERGE_COMPLETED_EVENT"]

CONTRACT_MERGE_COMPLETED_EVENT = "onex.contract.merge.completed"


class ModelContractMergeCompletedEvent(ModelContractValidationEventBase):
    """
    Event emitted when contract merge operation completes.

    This event indicates that contract merging finished successfully,
    producing an effective contract for runtime use. The ``run_id`` should
    match the corresponding started event for lifecycle correlation.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.contract.merge.completed).
        effective_contract_name: Identifier of the resulting effective contract.
        effective_contract_hash: Optional content hash of the effective contract
            for integrity verification and caching.
        overlays_applied_count: Number of overlays that were successfully applied.
        defaults_applied: Whether profile defaults were applied during merge.
        duration_ms: Time taken for the merge operation in milliseconds.
        warnings_count: Number of warnings generated during merge (default 0).
        diff_ref: Optional reference to stored diff showing changes from base.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractMergeCompletedEvent,
        ... )
        >>>
        >>> event = ModelContractMergeCompletedEvent(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     effective_contract_name="runtime-host-contract-effective-001",
        ...     effective_contract_hash="sha256:def456...",
        ...     overlays_applied_count=2,
        ...     defaults_applied=True,
        ...     duration_ms=50,
        ...     warnings_count=1,
        ...     diff_ref="diff://merge/001",
        ... )
        >>> event.event_type
        'onex.contract.merge.completed'

    Note:
        The ``effective_contract_hash`` can be used for caching - if the hash
        matches a cached version, the cached effective contract can be reused.

    .. versionadded:: 0.4.0
    """

    event_type: str = Field(
        default=CONTRACT_MERGE_COMPLETED_EVENT,
        description="Event type identifier.",
    )

    effective_contract_name: str = Field(
        ...,
        min_length=1,
        description="Identifier of the resulting effective contract.",
    )

    effective_contract_hash: str | None = Field(
        default=None,
        description="Optional content hash of the effective contract for "
        "integrity verification and caching.",
    )

    overlays_applied_count: int = Field(
        default=0,
        ge=0,
        description="Number of overlays that were successfully applied.",
    )

    defaults_applied: bool = Field(
        default=False,
        description="Whether profile defaults were applied during merge.",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Time taken for the merge operation in milliseconds.",
    )

    warnings_count: int = Field(
        default=0,
        ge=0,
        description="Number of warnings generated during merge.",
    )

    diff_ref: str | None = Field(
        default=None,
        description="Optional reference to stored diff showing changes "
        "from the base contract to the effective contract.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != CONTRACT_MERGE_COMPLETED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_MERGE_COMPLETED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        contract_name: str,
        run_id: UUID,
        effective_contract_name: str,
        duration_ms: int,
        *,
        effective_contract_hash: str | None = None,
        overlays_applied_count: int = 0,
        defaults_applied: bool = False,
        warnings_count: int = 0,
        diff_ref: str | None = None,
        actor: UUID | None = None,
        contract_ref: ModelContractRef | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelContractMergeCompletedEvent":
        """
        Factory method for creating a contract merge completed event.

        Args:
            contract_name: Identifier of the base contract that was merged.
            run_id: Unique identifier for this merge run (matches started event).
            effective_contract_name: Identifier of the resulting effective contract.
            duration_ms: Time taken for the merge in milliseconds.
            effective_contract_hash: Optional hash of the effective contract.
            overlays_applied_count: Number of overlays applied (default 0).
            defaults_applied: Whether defaults were applied (default False).
            warnings_count: Number of warnings generated (default 0).
            diff_ref: Optional reference to stored diff.
            actor: Optional UUID of the triggering node/service.
            contract_ref: Optional full contract reference.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelContractMergeCompletedEvent instance.
        """
        return cls(
            contract_name=contract_name,
            run_id=run_id,
            effective_contract_name=effective_contract_name,
            duration_ms=duration_ms,
            effective_contract_hash=effective_contract_hash,
            overlays_applied_count=overlays_applied_count,
            defaults_applied=defaults_applied,
            warnings_count=warnings_count,
            diff_ref=diff_ref,
            actor=actor,
            contract_ref=contract_ref,
            correlation_id=correlation_id,
        )
