"""
Metadata node collection core model.

Clean, focused implementation with proper typing and single responsibility.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Union

from pydantic import Field, RootModel, model_validator

from ..nodes.model_function_node import ModelFunctionNode
from .model_function_node_data import ModelFunctionNodeData
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_info import (
    ModelMetadataNodeInfo,
    ModelMetadataNodeType,
)
from .model_node_info_container import ModelNodeInfoContainer


class ModelMetadataNodeCollection(
    RootModel[dict[str, ModelFunctionNode | ModelFunctionNodeData]],
):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    """

    root: dict[str, ModelFunctionNode | ModelFunctionNodeData] = Field(
        default_factory=dict,
        description="Root dictionary containing metadata nodes",
    )

    def __init__(
        self,
        root: (
            Union[
                dict[str, ModelFunctionNode | ModelFunctionNodeData],
                ModelMetadataNodeCollection,
            ]
            | None
        ) = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with enhanced enterprise features."""
        if root is None:
            root = {}
        elif isinstance(root, ModelMetadataNodeCollection):
            root = root.root

        super().__init__(root)

        # Initialize enterprise features if not present
        if "_metadata_analytics" not in self.root:
            analytics_data = ModelMetadataNodeAnalytics().model_dump()
            self.root["_metadata_analytics"] = analytics_data  # type: ignore[assignment]

        if "_node_info" not in self.root:
            node_info_container = ModelNodeInfoContainer()
            self.root["_node_info"] = node_info_container  # type: ignore[assignment]
