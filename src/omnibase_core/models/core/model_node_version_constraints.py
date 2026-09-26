# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelNodeVersionConstraints - Container for node version constraints in scenarios."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_semver_constraint import ModelSemVerConstraint


class ModelNodeVersionConstraints(BaseModel):
    """Container for node version constraints in scenarios."""

    model_config = ConfigDict(extra="forbid")

    constraints: dict[str, ModelSemVerConstraint] = Field(
        default_factory=dict,
        description="Map of node names to their version constraints",
    )
