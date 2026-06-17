# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DataBindingContract — bind a UI component to a projection topic.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6).

A component reads truth only through ``/projection/{topic}`` with an explicit
ordering authority. There is no raw-DB binding and no client-side ordering
repair — the binding declares which column the upstream projection orders by
so the client never invents an order. Built on the
``ComponentManifest.projectionSchema`` + ``QuerySpec`` shapes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_binding_order_direction import EnumBindingOrderDirection

__all__ = ["ModelDataBindingContract"]


class ModelDataBindingContract(BaseModel):
    """Declares how a component binds to a projection topic.

    The binding names the projection topic, the ordering authority (the column
    the projection orders by and the direction), and the required fields the
    component consumes. Missing fields surface as a typed empty-state reason at
    render time, never a fallback literal.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    binding_id: str = Field(  # string-id-ok: semantic binding label, not a UUID
        ...,
        description="Stable semantic identifier for this binding within a component",
        min_length=1,
    )
    projection_topic: str = Field(
        ...,
        description="Canonical projection topic read via /projection/{topic}; no raw DB",
        min_length=1,
    )
    ordering_authority_field: str = Field(
        ...,
        description="Column the upstream projection orders by (explicit ordering authority)",
        min_length=1,
    )
    ordering_direction: EnumBindingOrderDirection = Field(
        default=EnumBindingOrderDirection.DESCENDING,
        description="Direction the ordering-authority field is ordered by upstream",
    )
    required_fields: tuple[str, ...] = Field(
        default=(),
        description="Projection row fields this component requires to render",
    )
    cursor_field: str | None = Field(
        default=None,
        description="Optional pagination cursor field exposed by the projection",
    )
