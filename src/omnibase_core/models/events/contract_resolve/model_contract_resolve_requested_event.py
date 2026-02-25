# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract resolve requested event model.

Emitted by NodeContractResolveCompute at the start of each resolution
operation, before any patches are applied.

Event type: ``onex.contract.resolve.requested``

.. versionadded:: OMN-2754
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "CONTRACT_RESOLVE_REQUESTED_EVENT",
    "ModelContractResolveRequestedEvent",
]

CONTRACT_RESOLVE_REQUESTED_EVENT = "onex.contract.resolve.requested"


class ModelContractResolveRequestedEvent(BaseModel):
    """Event emitted when a contract resolve operation is requested.

    Published at the start of the resolve operation before any merge occurs.
    Pairs with :class:`ModelContractResolveCompletedEvent` via ``run_id``.

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Always ``onex.contract.resolve.requested``.
        run_id: Correlates this event with its corresponding completed event.
        base_profile: Profile name from the base profile reference.
        patch_count: Number of patches to be applied.
        correlation_id: Optional tracing correlation ID.
        timestamp: UTC creation time.

    Example:
        >>> from uuid import uuid4
        >>> event = ModelContractResolveRequestedEvent.create(
        ...     run_id=uuid4(),
        ...     base_profile="compute_pure",
        ...     patch_count=2,
        ... )
        >>> event.event_type
        'onex.contract.resolve.requested'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event.",
    )

    event_type: str = Field(
        default=CONTRACT_RESOLVE_REQUESTED_EVENT,
        description="Event type identifier.",
    )

    run_id: UUID = Field(
        ...,
        description="Unique run identifier; correlates with completed event.",
    )

    base_profile: str = Field(
        ...,
        min_length=1,
        description="Profile name from the base_profile_ref.",
    )

    patch_count: int = Field(
        ...,
        ge=0,
        description="Number of patches to be applied.",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Optional tracing correlation ID.",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC creation time.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Ensure event_type matches the expected constant."""
        if v != CONTRACT_RESOLVE_REQUESTED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_RESOLVE_REQUESTED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        run_id: UUID,
        base_profile: str,
        patch_count: int,
        *,
        correlation_id: UUID | None = None,
    ) -> ModelContractResolveRequestedEvent:
        """Factory method for creating a resolve requested event.

        Args:
            run_id: Unique run identifier for lifecycle correlation.
            base_profile: Name of the base profile being resolved.
            patch_count: Number of patches to apply.
            correlation_id: Optional distributed tracing ID.

        Returns:
            A new :class:`ModelContractResolveRequestedEvent`.
        """
        return cls(
            run_id=run_id,
            base_profile=base_profile,
            patch_count=patch_count,
            correlation_id=correlation_id,
        )
