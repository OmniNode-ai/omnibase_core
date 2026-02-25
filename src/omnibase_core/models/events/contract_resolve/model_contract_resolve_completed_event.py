# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract resolve completed event model.

Emitted by NodeContractResolveCompute after all patches have been applied
and the resolved contract hash has been computed.

Event type: ``onex.contract.resolve.completed``

.. versionadded:: OMN-2754
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.nodes.contract_resolve.model_contract_resolve_output import (
    ModelOverlayRef,
    ModelResolverBuild,
)

__all__ = [
    "CONTRACT_RESOLVE_COMPLETED_EVENT",
    "ModelContractResolveCompletedEvent",
]

CONTRACT_RESOLVE_COMPLETED_EVENT = "onex.contract.resolve.completed"


class ModelContractResolveCompletedEvent(BaseModel):
    """Event emitted when a contract resolve operation completes.

    Carries the resolved contract hash, overlay refs, and resolver build
    metadata so consumers can cache or audit the resolution result.
    Pairs with :class:`ModelContractResolveRequestedEvent` via ``run_id``.

    This is the first event in the system to carry real, non-stub
    ``overlay_refs`` values (OMN-2754).

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Always ``onex.contract.resolve.completed``.
        run_id: Correlates with the corresponding requested event.
        resolved_hash: SHA-256 of the canonical resolved contract JSON.
        overlays_applied_count: Number of patches that were applied.
        overlay_refs: Structured metadata for each applied overlay (non-stub).
        resolver_build: Version and config metadata for the resolver.
        duration_ms: Wall-clock time for the resolution operation.
        correlation_id: Optional tracing correlation ID.
        timestamp: UTC creation time.

    Example:
        >>> from uuid import uuid4
        >>> event = ModelContractResolveCompletedEvent.create(
        ...     run_id=uuid4(),
        ...     resolved_hash="abc123...",
        ...     overlays_applied_count=2,
        ...     overlay_refs=[],
        ...     resolver_build=resolver_build,
        ...     duration_ms=12,
        ... )
        >>> event.event_type
        'onex.contract.resolve.completed'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event.",
    )

    event_type: str = Field(
        default=CONTRACT_RESOLVE_COMPLETED_EVENT,
        description="Event type identifier.",
    )

    run_id: UUID = Field(
        ...,
        description="Unique run identifier; correlates with requested event.",
    )

    resolved_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the canonical resolved contract JSON.",
    )

    overlays_applied_count: int = Field(
        ...,
        ge=0,
        description="Number of patches that were applied.",
    )

    overlay_refs: list[ModelOverlayRef] = Field(
        default_factory=list,
        description="Per-overlay metadata for each applied patch (non-stub).",
    )

    resolver_build: ModelResolverBuild = Field(
        ...,
        description="Version and config metadata for the resolver.",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Wall-clock duration of the resolution operation in milliseconds.",
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
        if v != CONTRACT_RESOLVE_COMPLETED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_RESOLVE_COMPLETED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        run_id: UUID,
        resolved_hash: str,
        overlays_applied_count: int,
        overlay_refs: list[ModelOverlayRef],
        resolver_build: ModelResolverBuild,
        duration_ms: int,
        *,
        correlation_id: UUID | None = None,
    ) -> ModelContractResolveCompletedEvent:
        """Factory method for creating a resolve completed event.

        Args:
            run_id: Unique run identifier for lifecycle correlation.
            resolved_hash: SHA-256 of the canonical resolved contract.
            overlays_applied_count: Number of overlays/patches applied.
            overlay_refs: Structured metadata for each applied overlay.
            resolver_build: Resolver version and config metadata.
            duration_ms: Wall-clock resolution time in milliseconds.
            correlation_id: Optional distributed tracing ID.

        Returns:
            A new :class:`ModelContractResolveCompletedEvent`.
        """
        return cls(
            run_id=run_id,
            resolved_hash=resolved_hash,
            overlays_applied_count=overlays_applied_count,
            overlay_refs=overlay_refs,
            resolver_build=resolver_build,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
