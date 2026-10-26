# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract declarations for runtime placement; consumer groups are runtime-owned."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_placement_mode import EnumPlacementMode
from omnibase_core.models.contracts.model_contract_placement_state import (
    ModelContractPlacementState,
)


class ModelContractPlacement(BaseModel):
    """Placement policy and optional primary failover recovery configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mode: EnumPlacementMode = Field(
        description="Run on any runtime or the elected primary."
    )
    failover_target_s: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    state: ModelContractPlacementState | None = Field(default=None)

    @staticmethod
    def requires_primary(node_type: EnumNodeType) -> bool:
        """Classify stateful node kinds, preserving the base model's UNKNOWN support."""
        return node_type != EnumNodeType.UNKNOWN and EnumNodeType.get_node_kind(
            node_type
        ) in {EnumNodeKind.ORCHESTRATOR, EnumNodeKind.REDUCER}

    @classmethod
    def for_node_type(cls, node_type: EnumNodeType) -> "ModelContractPlacement":
        """Resolve the effective policy for an omitted placement block."""
        return cls(
            mode=EnumPlacementMode.PRIMARY
            if cls.requires_primary(node_type)
            else EnumPlacementMode.ANY
        )
