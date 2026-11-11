# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Answer returned by the routing order node for a delegated task class."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_delegation_routing_order_refusal import (
    EnumDelegationRoutingOrderRefusal,
)
from omnibase_core.models.delegation.model_delegation_routing_order_rung import (
    ModelDelegationRoutingOrderRung,
)


class ModelDelegationRoutingOrderAnswer(BaseModel):
    """Ordered routing plan, or a stable refusal, for a delegated task class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    task_class: str
    rungs: tuple[ModelDelegationRoutingOrderRung, ...]
    refusal: EnumDelegationRoutingOrderRefusal | None
    detail: str

    @model_validator(mode="after")
    def _validate_answer_consistency(self) -> ModelDelegationRoutingOrderAnswer:
        if self.ok:
            if not self.rungs:
                raise ValueError("ok answer requires non-empty rungs")
            if self.refusal is not None:
                raise ValueError("ok answer must not carry a refusal")
        else:
            if self.refusal is None:
                raise ValueError("refused answer requires a refusal")
            if self.rungs:
                raise ValueError("refused answer must not carry rungs")
        return self


__all__ = ["ModelDelegationRoutingOrderAnswer"]
