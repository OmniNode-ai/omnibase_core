"""Aggregated outputs model for loop execution."""

from typing import Any, List

from pydantic import BaseModel, Field


class ModelLoopAggregatedOutputs(BaseModel):
    """Aggregated outputs from all loop iterations."""

    node_outputs: dict[str, List[Any]] = Field(
        default_factory=dict, description="Node outputs aggregated across iterations"
    )
