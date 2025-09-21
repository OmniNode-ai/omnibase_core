"""
Node information summary model.

Clean, strongly-typed replacement for node information dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_type import EnumMetadataNodeType
from ...enums.enum_status import EnumStatus
from ...utils.uuid_utilities import uuid_from_string
from .model_node_capabilities_summary import ModelNodeCapabilitiesSummary
from .model_node_configuration_summary import ModelNodeConfigurationSummary
from .model_node_core_info_summary import ModelNodeCoreInfoSummary


class ModelNodeInformationSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node information dict return types.

    Eliminates: dict[str, Any]

    With proper structured data using specific field types.
    """

    core_info: ModelNodeCoreInfoSummary = Field(
        description="Core node information summary"
    )
    capabilities: ModelNodeCapabilitiesSummary = Field(
        description="Node capabilities summary"
    )
    configuration: ModelNodeConfigurationSummary = Field(
        description="Node configuration summary"
    )
    is_fully_configured: bool = Field(description="Whether node is fully configured")


# Export the model
__all__ = ["ModelNodeInformationSummary"]
