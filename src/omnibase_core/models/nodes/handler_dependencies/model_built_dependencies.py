# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of building a handler's dependencies from the overlay (OMN-21595)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_dependency_binding_refusal_reason import (
    EnumDependencyBindingRefusalReason,
)


class ModelBuiltDependencies(BaseModel):
    """The built dependencies by protocol identifier, or the typed reason none were built.

    Attributes:
        refusal_reason: ``None`` when every dependency was built.
        unbound: The declared protocols the overlay does not bind.
        unregistered: The implementations the overlay names that no factory is registered for.
        dependencies: Protocol identifier to the built dependency; empty when refused.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, from_attributes=True, arbitrary_types_allowed=True
    )

    refusal_reason: EnumDependencyBindingRefusalReason | None = None
    unbound: tuple[str, ...] = ()
    unregistered: tuple[str, ...] = ()
    dependencies: dict[str, object] = Field(default_factory=dict)
