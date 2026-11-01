# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The lane overlay's bindings and the pure builder that reads only them (OMN-21595).

Every value is an overlay binding with no default in code. A handler declares protocol
identifiers in its contract (``handler_dependencies``); this model resolves them to
implementations and builds them, so a handler module reads no environment variable and
imports no concrete client. Nothing is built, and so nothing can subscribe, until every
declared protocol is bound.
"""

from collections.abc import Callable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_dependency_binding_refusal_reason import (
    EnumDependencyBindingRefusalReason,
)
from omnibase_core.models.nodes.handler_dependencies.model_built_dependencies import (
    ModelBuiltDependencies,
)
from omnibase_core.models.nodes.handler_dependencies.model_dependency_binding import (
    ModelDependencyBinding,
)
from omnibase_core.models.nodes.handler_dependencies.model_dependency_resolution import (
    ModelDependencyResolution,
)


class ModelOverlayBindings(BaseModel):
    """What one lane overlay binds.

    Attributes:
        dependencies: Handler dependency protocols bound to implementations.
        announcer_bus: The bus the announcer and the catalog publish and read on.
        catalog_store: The store the announcer keeps its previous inventory in.
        lazy_start_budget_seconds: How long a first request may wait for its node to start.
        reaper_flag_to_delete_days: How long a topic stays flagged before the reaper may
            delete it; ``None`` when the overlay sets no value, in which case the reaper
            never deletes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    dependencies: tuple[ModelDependencyBinding, ...]
    announcer_bus: ModelDependencyBinding
    catalog_store: ModelDependencyBinding
    lazy_start_budget_seconds: float = Field(gt=0)
    reaper_flag_to_delete_days: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _one_binding_per_protocol(self) -> "ModelOverlayBindings":
        protocols = [binding.protocol for binding in self.dependencies]
        if len(set(protocols)) != len(protocols):
            raise ValueError("the overlay binds a protocol more than once")
        return self

    def resolve(self, declared: Sequence[str]) -> ModelDependencyResolution:
        """Look up every declared protocol in the overlay and in nothing else.

        Args:
            declared: The contract's ``handler_dependencies``.
        """
        by_protocol = {binding.protocol: binding for binding in self.dependencies}
        unbound = tuple(dict.fromkeys(p for p in declared if p not in by_protocol))
        if unbound:
            return ModelDependencyResolution(
                refusal_reason=EnumDependencyBindingRefusalReason.DEPENDENCY_UNBOUND,
                unbound=unbound,
            )
        return ModelDependencyResolution(
            bindings=tuple(by_protocol[p] for p in dict.fromkeys(declared))
        )

    def build(
        self,
        declared: Sequence[str],
        factories: Mapping[str, Callable[[Mapping[str, str]], object]],
    ) -> ModelBuiltDependencies:
        """Build every declared dependency from its binding, or build none.

        No factory runs unless every declared protocol is bound and every bound
        implementation has a registered factory, so a refused contract has built
        nothing and subscribed to nothing.

        Args:
            declared: The contract's ``handler_dependencies``.
            factories: Implementation name to the factory that builds it; each satisfies
            ``ProtocolDependencyFactory``.
        """
        resolution = self.resolve(declared)
        if resolution.refusal_reason is not None:
            return ModelBuiltDependencies(
                refusal_reason=resolution.refusal_reason, unbound=resolution.unbound
            )
        unregistered = tuple(
            dict.fromkeys(
                b.implementation
                for b in resolution.bindings
                if b.implementation not in factories
            )
        )
        if unregistered:
            return ModelBuiltDependencies(
                refusal_reason=EnumDependencyBindingRefusalReason.IMPLEMENTATION_NOT_REGISTERED,
                unregistered=unregistered,
            )
        return ModelBuiltDependencies(
            dependencies={
                b.protocol: factories[b.implementation](b.config)
                for b in resolution.bindings
            }
        )

    def build_announcer_bus(
        self, factories: Mapping[str, Callable[[Mapping[str, str]], object]]
    ) -> ModelBuiltDependencies:
        """Build the announcer's bus from the overlay's ``announcer_bus`` binding alone."""
        return self._build_binding(self.announcer_bus, factories)

    def build_catalog_store(
        self, factories: Mapping[str, Callable[[Mapping[str, str]], object]]
    ) -> ModelBuiltDependencies:
        """Build the catalog's store from the overlay's ``catalog_store`` binding alone."""
        return self._build_binding(self.catalog_store, factories)

    @staticmethod
    def _build_binding(
        binding: ModelDependencyBinding,
        factories: Mapping[str, Callable[[Mapping[str, str]], object]],
    ) -> ModelBuiltDependencies:
        if binding.implementation not in factories:
            return ModelBuiltDependencies(
                refusal_reason=EnumDependencyBindingRefusalReason.IMPLEMENTATION_NOT_REGISTERED,
                unregistered=(binding.implementation,),
            )
        return ModelBuiltDependencies(
            dependencies={
                binding.protocol: factories[binding.implementation](binding.config)
            }
        )
