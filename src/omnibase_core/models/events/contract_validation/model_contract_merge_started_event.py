"""
Contract merge started event model.

This module provides the event model for when contract merge operations begin.
Contract merging combines base contracts with overlays and profiles to produce
an effective contract for runtime use.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_merge_started_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractMergeStartedEvent,
        )

Event Type:
    ``onex.contract.merge.started``

See Also:
    - :class:`ModelContractMergeCompletedEvent`: Emitted when merge completes

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

__all__ = ["ModelContractMergeStartedEvent", "CONTRACT_MERGE_STARTED_EVENT"]

CONTRACT_MERGE_STARTED_EVENT = "onex.contract.merge.started"


class ModelContractMergeStartedEvent(ModelContractValidationEventBase):
    """
    Event emitted when contract merge operation begins.

    Contract merging combines a base contract with overlays and profile-based
    defaults to produce an effective contract. This event marks the start
    of the merge process and should be followed by a completed event with
    the same run_id.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.contract.merge.started).
        merge_plan_name: Optional identifier of the merge plan being executed.
        profile_names: List of profile identifiers being applied during merge.
        overlay_refs: List of overlay references to be applied.
        resolver_config_hash: Optional hash of the resolver configuration
            for cache invalidation tracking.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractMergeStartedEvent,
        ... )
        >>>
        >>> event = ModelContractMergeStartedEvent(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     merge_plan_name="plan-001",
        ...     profile_names=["production", "high-availability"],
        ...     overlay_refs=["overlay://custom/timeout", "overlay://custom/retry"],
        ...     resolver_config_hash="sha256:abc123...",
        ... )
        >>> event.event_type
        'onex.contract.merge.started'

    Note:
        The ``resolver_config_hash`` can be used to detect when resolver
        configuration changes require cache invalidation of merged contracts.

    .. versionadded:: 0.4.0
    """

    event_type: str = Field(
        default=CONTRACT_MERGE_STARTED_EVENT,
        description="Event type identifier.",
    )

    merge_plan_name: str | None = Field(
        default=None,
        description="Optional identifier of the merge plan being executed.",
    )

    profile_names: list[str] = Field(
        default_factory=list,
        description="List of profile identifiers being applied during merge. "
        "Profiles provide default values and constraints for contracts.",
    )

    overlay_refs: list[str] = Field(
        default_factory=list,
        description="List of overlay references to be applied. Overlays modify "
        "specific contract fields without replacing the entire contract.",
    )

    resolver_config_hash: str | None = Field(
        default=None,
        description="Optional hash of the resolver configuration. Used for "
        "cache invalidation tracking when resolver settings change.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != CONTRACT_MERGE_STARTED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_MERGE_STARTED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        contract_name: str,
        run_id: UUID,
        *,
        merge_plan_name: str | None = None,
        profile_names: list[str] | None = None,
        overlay_refs: list[str] | None = None,
        resolver_config_hash: str | None = None,
        actor: UUID | None = None,
        contract_ref: ModelContractRef | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelContractMergeStartedEvent":
        """
        Factory method for creating a contract merge started event.

        Args:
            contract_name: Identifier of the base contract being merged.
            run_id: Unique identifier for this merge run.
            merge_plan_name: Optional identifier of the merge plan.
            profile_names: Optional list of profile identifiers.
            overlay_refs: Optional list of overlay references.
            resolver_config_hash: Optional hash of resolver configuration.
            actor: Optional UUID of the triggering node/service.
            contract_ref: Optional full contract reference.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelContractMergeStartedEvent instance.
        """
        return cls(
            contract_name=contract_name,
            run_id=run_id,
            merge_plan_name=merge_plan_name,
            profile_names=profile_names if profile_names is not None else [],
            overlay_refs=overlay_refs if overlay_refs is not None else [],
            resolver_config_hash=resolver_config_hash,
            actor=actor,
            contract_ref=contract_ref,
            correlation_id=correlation_id,
        )
