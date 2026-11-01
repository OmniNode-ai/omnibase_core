# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of resolving a contract's declared dependencies against the overlay (OMN-21595)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_dependency_binding_refusal_reason import (
    EnumDependencyBindingRefusalReason,
)
from omnibase_core.models.nodes.handler_dependencies.model_dependency_binding import (
    ModelDependencyBinding,
)


class ModelDependencyResolution(BaseModel):
    """The bindings for every declared protocol, or the typed reason there are none.

    Attributes:
        refusal_reason: ``None`` when every declared protocol is bound.
        unbound: The declared protocols the overlay does not bind, in declared order.
        bindings: The bindings of the declared protocols, in declared order; empty when refused.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    refusal_reason: EnumDependencyBindingRefusalReason | None = None
    unbound: tuple[str, ...] = ()
    bindings: tuple[ModelDependencyBinding, ...] = ()
