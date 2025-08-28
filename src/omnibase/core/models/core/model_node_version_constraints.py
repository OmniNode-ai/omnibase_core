"""ModelNodeVersionConstraints - Container for node version constraints in scenarios."""

from typing import Dict

from pydantic import BaseModel, Field

from omnibase.model.core.model_semver_constraint import ModelSemVerConstraint


class ModelNodeVersionConstraints(BaseModel):
    """Container for node version constraints in scenarios."""

    constraints: Dict[str, ModelSemVerConstraint] = Field(
        default_factory=dict,
        description="Map of node names to their version constraints",
    )
