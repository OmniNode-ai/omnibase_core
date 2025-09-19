"""
Metadata node collection core model.

Clean, focused implementation with proper typing and single responsibility.
Follows ONEX one-model-per-file naming conventions.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, RootModel, computed_field, model_validator

from omnibase_core.enums.nodes.enum_security_level import EnumSecurityLevel
from omnibase_core.models.core.model_function_node import ModelFunctionNode

from .model_collection_analytics_report import ModelCollectionAnalyticsReport
from .model_collection_metadata import ModelCollectionMetadata
from .model_collection_node_breakdown import ModelCollectionNodeBreakdown
from .model_collection_node_validation_result import ModelCollectionNodeValidationResult
from .model_collection_performance_metrics import ModelCollectionPerformanceMetrics
from .model_collection_validation_result import ModelCollectionValidationResult
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_info import (
    EnumMetadataNodeComplexity,
    EnumMetadataNodeStatus,
    EnumMetadataNodeType,
    ModelMetadataNodeInfo,
)
from .model_metadata_node_usage_metrics import ModelMetadataNodeUsageMetrics


class ModelMetadataNodeCollection(
    RootModel[Dict[str, Union[ModelFunctionNode, Dict[str, str], Dict[str, int]]]]
):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    """

    root: Dict[str, Union[ModelFunctionNode, Dict[str, str], Dict[str, int]]] = Field(
        default_factory=dict, description="Root dictionary containing metadata nodes"
    )

    def __init__(
        self,
        root: Optional[
            Union[
                Dict[str, Union[ModelFunctionNode, Dict[str, str], Dict[str, int]]],
                "ModelMetadataNodeCollection",
            ]
        ] = None,
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
            self.root["_metadata_analytics"] = ModelMetadataNodeAnalytics(
                total_nodes=0,
                total_invocations=0,
                overall_success_rate=100.0,
                avg_collection_performance=0.0,
                health_score=100.0,
                documentation_coverage=0.0,
                validation_compliance=100.0,
            ).model_dump()

        if "_node_info" not in self.root:
            self.root["_node_info"] = {}

    @model_validator(mode="before")
    @classmethod
    def coerce_node_values(
        cls,
        data: Union[Dict[str, Any], "ModelMetadataNodeCollection", None],
    ) -> Dict[str, Any]:
        """Enhanced node value coercion with validation and enhancement."""
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                # Skip enterprise metadata fields
                if k.startswith(("_metadata_", "_node_")):
                    new_data[k] = v
                    continue

                if isinstance(v, dict):
                    # Enhanced ModelFunctionNode creation with validation
                    try:
                        function_node = ModelFunctionNode(**v)
                        new_data[k] = function_node
                    except Exception:
                        # Fallback to raw dict if ModelFunctionNode creation fails
                        new_data[k] = v
                else:
                    new_data[k] = v
            return new_data

        if isinstance(data, ModelMetadataNodeCollection):
            return data.root

        # Handle None case (only remaining possibility)
        return {}  # type: ignore[unreachable]

    @model_validator(mode="after")
    def check_function_names_and_enhance(
        self,
    ) -> "ModelMetadataNodeCollection":
        """Enhanced validation with analytics updates."""
        node_count = 0
        nodes_by_type: Dict[str, int] = {}
        nodes_by_status: Dict[str, int] = {}
        nodes_by_complexity: Dict[str, int] = {}

        for name, _node_data in self.root.items():
            # Skip enterprise metadata fields
            if name.startswith(("_metadata_", "_node_")):
                continue

            # Validate function name
            if not name.isidentifier():
                msg = f"Invalid function name: {name}"
                raise ValueError(msg)

            node_count += 1

            # Update analytics if node info exists
            node_info_dict = self.root.get("_node_info", {})
            if isinstance(node_info_dict, dict) and name in node_info_dict:
                node_info_data = node_info_dict[name]
                if isinstance(node_info_data, dict):
                    node_type = node_info_data.get("node_type", "function")
                    node_status = node_info_data.get("status", "active")
                    node_complexity = node_info_data.get("complexity", "simple")

                    nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1
                    nodes_by_status[node_status] = (
                        nodes_by_status.get(node_status, 0) + 1
                    )
                    nodes_by_complexity[node_complexity] = (
                        nodes_by_complexity.get(node_complexity, 0) + 1
                    )

        # Update analytics with proper type handling
        analytics_data = self.root.get("_metadata_analytics", {})
        if isinstance(analytics_data, dict):
            # Create a new ModelMetadataNodeAnalytics instance with updated data
            updated_analytics = ModelMetadataNodeAnalytics(
                total_nodes=node_count,
                total_invocations=int(analytics_data.get("total_invocations", 0)),
                overall_success_rate=float(
                    analytics_data.get("overall_success_rate", 100.0)
                ),
                avg_collection_performance=float(
                    analytics_data.get("avg_collection_performance", 0.0)
                ),
                health_score=float(analytics_data.get("health_score", 100.0)),
                documentation_coverage=float(
                    analytics_data.get("documentation_coverage", 0.0)
                ),
                validation_compliance=float(
                    analytics_data.get("validation_compliance", 100.0)
                ),
                nodes_by_type=nodes_by_type,
                nodes_by_status=nodes_by_status,
                nodes_by_complexity=nodes_by_complexity,
            )
            self.root["_metadata_analytics"] = updated_analytics.model_dump()
        else:
            # Create new analytics if none exist
            new_analytics = ModelMetadataNodeAnalytics(
                total_nodes=node_count,
                total_invocations=0,
                overall_success_rate=100.0,
                avg_collection_performance=0.0,
                health_score=100.0,
                documentation_coverage=0.0,
                validation_compliance=100.0,
                nodes_by_type=nodes_by_type,
                nodes_by_status=nodes_by_status,
                nodes_by_complexity=nodes_by_complexity,
            )
            self.root["_metadata_analytics"] = new_analytics.model_dump()

        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def collection_id(self) -> str:
        """Generate unique identifier for this collection."""
        node_names = sorted([k for k in self.root if not k.startswith("_")])
        content = f"metadata_nodes:{':'.join(node_names)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def node_count(self) -> int:
        """Get total number of nodes (excluding metadata)."""
        return len([k for k in self.root if not k.startswith("_")])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def analytics(self) -> ModelMetadataNodeAnalytics:
        """Get collection analytics."""
        analytics_data = self.root.get("_metadata_analytics", {})
        if isinstance(analytics_data, dict):
            return ModelMetadataNodeAnalytics(**analytics_data)
        else:
            return ModelMetadataNodeAnalytics(
                total_nodes=0,
                total_invocations=0,
                overall_success_rate=100.0,
                avg_collection_performance=0.0,
                health_score=100.0,
                documentation_coverage=0.0,
                validation_compliance=100.0,
            )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def health_score(self) -> float:
        """Calculate overall collection health score."""
        if self.node_count == 0:
            return 100.0

        analytics = self.analytics

        # Base score from success rate
        base_score = analytics.overall_success_rate

        # Penalty for deprecated/disabled nodes
        deprecated_ratio = analytics.nodes_by_status.get("deprecated", 0) / max(
            analytics.total_nodes,
            1,
        )
        disabled_ratio = analytics.nodes_by_status.get("disabled", 0) / max(
            analytics.total_nodes,
            1,
        )

        penalty = (deprecated_ratio + disabled_ratio) * 20  # Up to 20 point penalty

        # Bonus for good documentation coverage
        doc_bonus = analytics.documentation_coverage * 0.1  # Up to 10 point bonus

        return max(0.0, min(100.0, base_score - penalty + doc_bonus))

    def add_node(
        self,
        name: str,
        node_data: Union[ModelFunctionNode, Dict[str, str]],
        node_info: Optional[ModelMetadataNodeInfo] = None,
    ) -> bool:
        """
        Add a node to the collection with enhanced metadata tracking.

        Args:
            name: Node name
            node_data: Node data (ModelFunctionNode, dict, etc.)
            node_info: Optional enhanced node information

        Returns:
            bool: True if node added successfully
        """
        try:
            # Validate node name
            if not name.isidentifier():
                return False

            # Add the node data
            if isinstance(node_data, dict):
                try:
                    self.root[name] = ModelFunctionNode(**node_data)
                except Exception:
                    self.root[name] = node_data
            else:
                self.root[name] = node_data

            # Add node info if provided
            if node_info:
                if "_node_info" not in self.root:
                    self.root["_node_info"] = {}
                node_info_dict = self.root["_node_info"]
                if isinstance(node_info_dict, dict):
                    node_info_dict[name] = node_info.model_dump()
            else:
                node_info_dict = self.root.get("_node_info", {})
                if isinstance(node_info_dict, dict) and name not in node_info_dict:
                    # Create default node info
                    default_info = ModelMetadataNodeInfo(
                        name=name,
                        node_type=EnumMetadataNodeType.FUNCTION,
                        status=EnumMetadataNodeStatus.ACTIVE,
                        complexity=EnumMetadataNodeComplexity.SIMPLE,
                        description="",
                        documentation="",
                        author="Unknown",
                        version="1.0.0",
                        replaces=None,
                        security_level=EnumSecurityLevel.STANDARD,
                    )
                    if "_node_info" not in self.root:
                        self.root["_node_info"] = {}
                    node_info_dict = self.root["_node_info"]
                    if isinstance(node_info_dict, dict):
                        node_info_dict[name] = default_info.model_dump()

            # Update analytics
            self._update_analytics()

            return True

        except Exception:
            return False

    def remove_node(self, name: str) -> bool:
        """Remove a node from the collection."""
        if name in self.root and not name.startswith("_"):
            del self.root[name]

            # Remove node info if exists
            node_info_dict = self.root.get("_node_info")
            if isinstance(node_info_dict, dict) and name in node_info_dict:
                del node_info_dict[name]

            # Update analytics
            self._update_analytics()
            return True

        return False

    def get_node(self, name: str) -> Optional[Union[ModelFunctionNode, Dict[str, str]]]:
        """Get a node by name."""
        return self.root.get(name)

    def get_node_info(self, name: str) -> Optional[ModelMetadataNodeInfo]:
        """Get enhanced node information."""
        node_info_dict = self.root.get("_node_info", {})
        if isinstance(node_info_dict, dict):
            node_info_data = node_info_dict.get(name)
            if node_info_data and isinstance(node_info_data, dict):
                return ModelMetadataNodeInfo(**node_info_data)
        return None

    def update_node_info(self, name: str, node_info: ModelMetadataNodeInfo) -> bool:
        """Update node information."""
        if name not in self.root or name.startswith("_"):
            return False

        if "_node_info" not in self.root:
            self.root["_node_info"] = {}

        node_info_dict = self.root["_node_info"]
        if isinstance(node_info_dict, dict):
            node_info_dict[name] = node_info.model_dump()
        self._update_analytics()
        return True

    def _update_analytics(self) -> None:
        """Internal method to update collection analytics."""
        analytics_dict = self.root.get("_metadata_analytics", {})
        analytics_data = analytics_dict if isinstance(analytics_dict, dict) else {}

        # Count nodes by various categories
        nodes_by_type: Dict[str, int] = {}
        nodes_by_status: Dict[str, int] = {}
        nodes_by_complexity: Dict[str, int] = {}
        total_invocations = 0
        total_success = 0

        node_count = 0
        for name in self.root:
            if name.startswith("_"):
                continue

            node_count += 1
            node_info = self.get_node_info(name)
            if node_info:
                # Count by categories
                nodes_by_type[node_info.node_type.value] = (
                    nodes_by_type.get(node_info.node_type.value, 0) + 1
                )
                nodes_by_status[node_info.status.value] = (
                    nodes_by_status.get(node_info.status.value, 0) + 1
                )
                nodes_by_complexity[node_info.complexity.value] = (
                    nodes_by_complexity.get(node_info.complexity.value, 0) + 1
                )

                # Aggregate usage metrics
                total_invocations += node_info.usage_metrics.total_invocations
                total_success += node_info.usage_metrics.success_count

        # Calculate overall success rate
        overall_success_rate = (
            (total_success / max(total_invocations, 1)) * 100
            if total_invocations > 0
            else 100.0
        )

        # Update analytics - mixed types in analytics data
        update_dict = {
            "last_modified": datetime.now().isoformat(),
            "total_nodes": node_count,
            "nodes_by_type": nodes_by_type,
            "nodes_by_status": nodes_by_status,
            "nodes_by_complexity": nodes_by_complexity,
            "total_invocations": total_invocations,
            "overall_success_rate": overall_success_rate,
            "health_score": self.health_score,
        }
        analytics_data.update(update_dict)

        self.root["_metadata_analytics"] = analytics_data

    # Factory methods for common scenarios
    @classmethod
    def create_empty_collection(cls) -> "ModelMetadataNodeCollection":
        """Create an empty metadata node collection."""
        return cls({})

    @classmethod
    def create_from_function_nodes(
        cls,
        nodes_dict: Dict[str, ModelFunctionNode],
    ) -> "ModelMetadataNodeCollection":
        """Create collection from existing ModelFunctionNode dictionary."""
        collection = cls(nodes_dict)

        # Add basic node info for each node
        for name, node in nodes_dict.items():
            if hasattr(node, "name") and hasattr(node, "description"):
                node_info = ModelMetadataNodeInfo(
                    name=name,
                    description=getattr(node, "description", ""),
                    node_type=EnumMetadataNodeType.FUNCTION,
                    status=EnumMetadataNodeStatus.ACTIVE,
                    complexity=EnumMetadataNodeComplexity.SIMPLE,
                    documentation="",
                    author="Unknown",
                    version="1.0.0",
                    replaces=None,
                    security_level=EnumSecurityLevel.STANDARD,
                )
                collection.update_node_info(name, node_info)

        return collection

    @classmethod
    def create_documentation_collection(
        cls,
        name: str = "documentation",
    ) -> "ModelMetadataNodeCollection":
        """Create a collection optimized for documentation nodes."""
        collection = cls({})

        # Set up analytics for documentation focus
        analytics_data = {
            "collection_created": datetime.now().isoformat(),
            "collection_name": name,
            "collection_purpose": "documentation",
            "documentation_coverage": 0.0,
        }

        collection.root["_metadata_analytics"] = analytics_data
        return collection


# Export for use
__all__ = ["ModelMetadataNodeCollection"]
