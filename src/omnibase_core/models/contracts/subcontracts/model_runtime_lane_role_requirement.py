# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The lane roles a node contract needs (OMN-19746).

Declared as a top-level ``runtime_lane_roles`` list in ``contract.yaml``. A
contract never names a lane: which lanes exist, and what each is for, is the
business of the deployment's ``runtime.lane`` overlay document. The loader
attaches the node only on a runtime whose declared lane holds every role
listed. A contract that omits the field is unscoped by lane.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_runtime_lane_role import EnumRuntimeLaneRole
from omnibase_core.models.config_overlay.model_runtime_lane_declaration import (
    normalize_runtime_lane_roles,
)

if TYPE_CHECKING:
    from omnibase_core.models.config_overlay.model_runtime_lane_declaration import (
        ModelRuntimeLaneDeclaration,
    )

__all__ = ["ModelRuntimeLaneRoleRequirement"]


class ModelRuntimeLaneRoleRequirement(BaseModel):
    """Every role a runtime lane must hold for a node to attach there."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    roles: tuple[EnumRuntimeLaneRole, ...] = Field(
        ...,
        min_length=1,
        description=(
            "Roles the runtime's lane must hold, all of them. Never empty: the "
            "way to say 'any lane' is to omit runtime_lane_roles."
        ),
    )

    @field_validator("roles", mode="before")
    @classmethod
    def _parse_roles(cls, value: object) -> tuple[EnumRuntimeLaneRole, ...]:
        return normalize_runtime_lane_roles(value)

    def admits(self, declaration: ModelRuntimeLaneDeclaration) -> bool:
        """Return whether a runtime with this lane declaration may attach the node."""
        return declaration.has_roles(self.roles)
