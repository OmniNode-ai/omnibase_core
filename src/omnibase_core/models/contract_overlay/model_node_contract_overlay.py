# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The contract section of a node's contract overlay, as a registered resolver reads it (OMN-22469).

It mirrors ModelNodeBrokerBinding (OMN-22362). Handler wiring deep-merges it over the packaged
contract so a handler that asks for effective_contract sees overlay keys, and core never reads the
overlay file itself because only the package that owns the workspace layout can.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.merge.merge_rules import merge_dict
from omnibase_core.models.contract_overlay.model_node_contract_overlay_resolution_error import (
    ModelNodeContractOverlayResolutionError,
)
from omnibase_core.types.type_json import JsonType

NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP: Final[str] = (
    "onex.node_contract_overlay_resolvers"
)


class ModelNodeContractOverlay(BaseModel):
    """What a resolver answers for one node: the contract keys its overlay sets.

    ``contract`` is empty, and ``overlay_path`` is ``None``, when the node has no overlay; the
    packaged contract then stands unchanged.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str = Field(min_length=1)
    overlay_path: Path | None = Field(
        default=None, description="The overlay file the contract section was read from."
    )
    contract: dict[str, JsonType] = Field(default_factory=dict)

    @classmethod
    def for_node(cls, node_id: str) -> Self:
        """The contract section ``node_id``'s overlay declares, from the one registered resolver.

        Exactly one provider may be installed under
        :data:`NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP`: none would leave the caller
        guessing, and two would let install order pick. The provider is checked structurally,
        as :meth:`ModelNodeBrokerBinding.for_node` checks its own.

        Raises:
            ModelNodeContractOverlayResolutionError: no or several providers, or the provider
                refuses or answers the wrong type.
        """
        providers = list(
            entry_points(group=NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP)
        )
        if not providers:
            raise ModelNodeContractOverlayResolutionError(
                "no node contract overlay resolver is installed, so the node's contract overlay "
                "cannot be read. Install the package that registers one under "
                f"`{NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP}`."
            )
        if len(providers) > 1:
            found = ", ".join(sorted(f"{ep.name} ({ep.value})" for ep in providers))
            raise ModelNodeContractOverlayResolutionError(
                f"more than one node contract overlay resolver is registered ({found}); "
                "uninstall the extra provider so one declaration answers."
            )
        loaded = providers[0].load()
        resolver = loaded() if isinstance(loaded, type) else loaded
        resolve = getattr(resolver, "resolve_contract_overlay", None)
        if not callable(resolve):
            raise ModelNodeContractOverlayResolutionError(
                f"node contract overlay resolver {providers[0].value!r} does not provide "
                "resolve_contract_overlay"
            )
        overlay = resolve(node_id)
        if not isinstance(overlay, cls):
            raise ModelNodeContractOverlayResolutionError(
                f"node contract overlay resolver {providers[0].value!r} answered "
                f"{type(overlay).__name__}, not {cls.__name__}"
            )
        return overlay

    def merged_into(self, packaged: dict[str, JsonType]) -> dict[str, JsonType]:
        """The packaged contract with this overlay's keys over it; ``packaged`` is not changed."""
        return merge_dict(packaged, self.contract)


__all__ = [
    "NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP",
    "ModelNodeContractOverlay",
]
