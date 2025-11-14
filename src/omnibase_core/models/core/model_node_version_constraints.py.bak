from typing import Any

"""ModelNodeVersionConstraints - Container for node version constraints in scenarios."""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver_constraint import ModelSemVerConstraint
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeVersionConstraints(BaseModel):
    """Container for node version constraints in scenarios."""

    constraints: dict[str, ModelSemVerConstraint] = Field(
        default_factory=dict,
        description="Map of node names to their version constraints",
    )
