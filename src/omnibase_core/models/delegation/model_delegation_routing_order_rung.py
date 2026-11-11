# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One rung of a delegation routing order answer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_delegation_routing_order_rung_kind import (
    EnumDelegationRoutingOrderRungKind,
)


class ModelDelegationRoutingOrderRung(BaseModel):
    """A single position in the ordered routing plan for a task class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    position: int = Field(ge=0)
    tier: str = Field(min_length=1)
    kind: EnumDelegationRoutingOrderRungKind
    backend_ids: tuple[str, ...] = Field(
        description=(
            "The backends of a ladder tier that serve the task class, or the "
            "single harness backend id."
        )
    )
    harness: str | None
    model_name: str | None
    max_retries: int | None = Field(default=None, ge=0)
    attempts: int = Field(ge=1)
    refusals: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_rung_consistency(self) -> ModelDelegationRoutingOrderRung:
        if self.kind is EnumDelegationRoutingOrderRungKind.LADDER:
            if self.max_retries is None:
                raise ValueError("ladder rung requires max_retries")
            if self.attempts != self.max_retries + 1:
                raise ValueError("ladder rung attempts must equal max_retries + 1")
        else:
            if self.max_retries is not None:
                raise ValueError("harness rung must not set max_retries")
            if self.harness is None:
                raise ValueError("harness rung requires a harness name")
            if self.attempts != 1:
                raise ValueError("harness rung attempts must be 1")
        return self


__all__ = ["ModelDelegationRoutingOrderRung"]
