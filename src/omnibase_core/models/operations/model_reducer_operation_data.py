from __future__ import annotations

from pydantic import Field

"""
Reducer node operation data for state management and aggregation.
"""


from typing import Literal

from omnibase_core.enums.enum_node_type import EnumNodeType

from .model_operation_data_base import ModelOperationDataBase


class ModelReducerOperationData(ModelOperationDataBase):
    """Reducer node operation data for state management and aggregation."""

    operation_type: Literal[EnumNodeType.REDUCER] = Field(
        default=EnumNodeType.REDUCER,
        description="Reducer operation type",
    )
    aggregation_type: str = Field(default=..., description="Type of data aggregation")
    state_key: str = Field(default=..., description="State key for aggregation")
    persistence_config: dict[str, str] = Field(
        default_factory=dict,
        description="Data persistence configuration",
    )
    consistency_level: str = Field(
        default="eventual",
        description="Data consistency requirements",
    )


__all__ = ["ModelReducerOperationData"]
