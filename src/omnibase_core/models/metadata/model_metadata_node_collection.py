"""
Metadata Node Collection Model.

Clean, focused implementation with proper typing and single responsibility following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import Field, RootModel

from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_node_info_container import ModelNodeInfoContainer
from .model_node_union import ModelNodeUnion


class ModelMetadataNodeCollection(
    RootModel[dict[str, ModelNodeUnion]],
):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    """

    root: dict[str, ModelNodeUnion] = Field(
        default_factory=dict,
        description="Root dictionary containing metadata nodes",
    )

    def __init__(
        self,
        root: dict[str, ModelNodeUnion] | ModelMetadataNodeCollection | None = None,
        **kwargs: object,
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
