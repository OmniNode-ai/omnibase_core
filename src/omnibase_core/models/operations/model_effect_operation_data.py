from __future__ import annotations

from pydantic import Field

"""
Effect node operation data for external interactions.
"""


from typing import Literal

from omnibase_core.enums.enum_node_type import EnumNodeType

from .model_operation_data_base import ModelOperationDataBase


class ModelEffectOperationData(ModelOperationDataBase):
    """Effect node operation data for external interactions."""

    operation_type: Literal[EnumNodeType.EFFECT] = Field(
        default=EnumNodeType.EFFECT,
        description="Effect operation type",
    )
    target_system: str = Field(default=..., description="Target external system")
    interaction_type: str = Field(
        default=..., description="Type of external interaction"
    )
    retry_policy: dict[str, int] = Field(
        default_factory=dict,
        description="Retry policy configuration",
    )
    side_effect_tracking: bool = Field(
        default=True,
        description="Whether to track side effects",
    )


__all__ = ["ModelEffectOperationData"]
