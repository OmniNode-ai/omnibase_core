"""Aggregated outputs model for loop execution."""

from typing import Any

from pydantic import BaseModel, Field


class ModelLoopAggregatedOutputs(BaseModel):
    """Aggregated outputs from all loop iterations."""

    node_outputs: dict[str, list[Any]] = Field(
        default_factory=dict,
        description="Node outputs aggregated across iterations",
    )
