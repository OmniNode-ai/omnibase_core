# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelProjectionContract — runtime contract for a CQRS projection (OMN-11192)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_degraded_behavior import EnumDegradedBehavior
from omnibase_core.models.projection.model_cursor_contract import ModelCursorContract


class ModelProjectionContract(BaseModel):
    """Runtime contract declaring freshness SLA, ordering, and degraded semantics for a projection."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    projection_name: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this projection.",
    )

    source_topics: tuple[str, ...] = Field(
        ...,
        description="Kafka topics this projection consumes.",
    )

    schema_model: str = Field(
        ...,
        min_length=1,
        description="Fully-qualified Pydantic model name for projection rows.",
    )

    freshness_sla_seconds: int = Field(
        ...,
        gt=0,
        description="Maximum acceptable lag in seconds before the projection is considered stale.",
    )

    freshness_field: str = Field(
        ...,
        min_length=1,
        description="Column checked to determine projection staleness.",
    )

    freshness_source_table: str = Field(
        ...,
        min_length=1,
        description="Table queried when checking freshness_field.",
    )

    degraded_semantics: EnumDegradedBehavior = Field(
        ...,
        description="Behaviour when projection freshness SLA is breached. No default — must be explicit.",
    )

    cursor: ModelCursorContract = Field(
        ...,
        description="Cursor mechanism for this projection.",
    )

    ordering_contract_ref: str | None = Field(
        default=None,
        description="Name of the ModelProjectionOrderingContract constant, if ordering is defined.",
    )
