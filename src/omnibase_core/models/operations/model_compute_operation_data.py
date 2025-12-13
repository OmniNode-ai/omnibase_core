"""
Compute node operation data for business logic and calculations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_node_type import EnumNodeType

from .model_operation_data_base import ModelOperationDataBase


class ModelComputeOperationData(ModelOperationDataBase):
    """Compute node operation data for business logic and calculations."""

    operation_type: Literal[EnumNodeType.COMPUTE_GENERIC] = Field(
        default=EnumNodeType.COMPUTE_GENERIC,
        description="Compute operation type",
    )
    algorithm_type: str = Field(
        default=..., description="Type of algorithm or computation"
    )
    computation_resources: dict[str, float] = Field(
        default_factory=dict,
        description="Required computation resources",
    )
    optimization_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Performance optimization hints",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Whether computation can be parallelized",
    )


__all__ = ["ModelComputeOperationData"]
