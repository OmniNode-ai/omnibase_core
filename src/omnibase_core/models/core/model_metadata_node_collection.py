"""
Metadata node collection models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

import hashlib
from datetime import datetime
from typing import Any, Type, Union

from pydantic import RootModel, computed_field, model_validator

from omnibase_core.models.core.model_function_node import ModelFunctionNode

from .model_metadata_collection_types import (
    ModelAnalyticsReport,
    ModelCollectionMetadata,
    ModelCollectionValidationResult,
    ModelNodeBreakdown,
    ModelNodeValidationResult,
    ModelPerformanceMetrics,
)
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_info import (
    ModelMetadataNodeComplexity,
    ModelMetadataNodeInfo,
    ModelMetadataNodeStatus,
    ModelMetadataNodeType,
)

# Import separated models
from .model_metadata_node_usage_metrics import ModelMetadataNodeUsageMetrics


class ModelMetadataNodeCollection(
    RootModel[dict[str, Union[ModelFunctionNode, dict[str, str], dict[str, int]]]]
):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Enhanced with comprehensive node analytics, usage tracking, performance monitoring,
    and operational insights for documentation and metadata management systems.
    """

    def __init__(
        self,
        root: Union[
            dict[str, Union[ModelFunctionNode, dict[str, str], dict[str, int]]],
            "ModelMetadataNodeCollection",
            None,
        ] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with enhanced enterprise features."""
        if root is None:
            root = {}
        elif isinstance(root, ModelMetadataNodeCollection):
            root = root.root

        # Initialize the root dictionary
        super().__init__(root)

        # Initialize enterprise features if not present
        if "_metadata_analytics" not in self.root:
            self.root["_metadata_analytics"] = ModelMetadataNodeAnalytics().model_dump()

        if "_node_info" not in self.root:
            self.root["_node_info"] = {}

    @model_validator(mode="before")
    @classmethod
    def coerce_node_values(
        cls: Type["ModelMetadataNodeCollection"],
        data: Union[dict, "ModelMetadataNodeCollection", None],
    ) -> dict[str, Any]:
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
                        function_node = ModelFunctionNode(
                            **v
                        )  # Direct Pydantic instantiation (ONEX compliance)
                        new_data[k] = function_node
                    except Exception:
                        # Fallback to raw dict if ModelFunctionNode creation fails
                        new_data[k] = v
                else:
                    new_data[k] = v
            return new_data

        if isinstance(data, ModelMetadataNodeCollection):
            return data.root

        return data or {}

    @model_validator(mode="after")
    def check_function_names_and_enhance(
        self: "ModelMetadataNodeCollection",
    ) -> "ModelMetadataNodeCollection":
        """Enhanced validation with analytics updates."""
        node_count = 0
        nodes_by_type: dict[str, int] = {}
        nodes_by_status: dict[str, int] = {}
        nodes_by_complexity: dict[str, int] = {}

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
            if name in self.root.get("_node_info", {}):
                node_info_data = self.root["_node_info"][name]
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

        # Update analytics
        analytics_data = self.root.get("_metadata_analytics", {})
        if isinstance(analytics_data, dict):
            analytics_data.update(
                {
                    "last_modified": datetime.now().isoformat(),
                    "total_nodes": node_count,
                    "nodes_by_type": nodes_by_type,
                    "nodes_by_status": nodes_by_status,
                    "nodes_by_complexity": nodes_by_complexity,
                },
            )
        self.root["_metadata_analytics"] = analytics_data

        return self

    @computed_field
    def collection_id(self) -> str:
        """Generate unique identifier for this collection."""
        node_names = sorted([k for k in self.root if not k.startswith("_")])
        content = f"metadata_nodes:{':'.join(node_names)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @computed_field
    def node_count(self) -> int:
        """Get total number of nodes (excluding metadata)."""
        return len([k for k in self.root if not k.startswith("_")])

    @computed_field
    def analytics(self) -> ModelMetadataNodeAnalytics:
        """Get collection analytics."""
        analytics_data = self.root.get("_metadata_analytics", {})
        if isinstance(analytics_data, dict):
            return ModelMetadataNodeAnalytics(**analytics_data)
        else:
            return ModelMetadataNodeAnalytics()

    @computed_field
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
        node_data: Union[ModelFunctionNode, dict[str, str]],
        node_info: ModelMetadataNodeInfo | None = None,
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
                    self.root[name] = ModelFunctionNode(
                        **node_data
                    )  # Direct Pydantic instantiation (ONEX compliance)
                except Exception:
                    self.root[name] = node_data
            else:
                self.root[name] = node_data

            # Add node info if provided
            if node_info:
                if "_node_info" not in self.root:
                    self.root["_node_info"] = {}
                self.root["_node_info"][name] = node_info.model_dump()
            elif name not in self.root.get("_node_info", {}):
                # Create default node info
                default_info = ModelMetadataNodeInfo(name=name)
                if "_node_info" not in self.root:
                    self.root["_node_info"] = {}
                self.root["_node_info"][name] = default_info.model_dump()

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
            if "_node_info" in self.root and name in self.root["_node_info"]:
                del self.root["_node_info"][name]

            # Update analytics
            self._update_analytics()
            return True

        return False

    def get_node(self, name: str) -> Union[ModelFunctionNode, dict[str, str], None]:
        """Get a node by name."""
        return self.root.get(name, None)

    def get_node_info(self, name: str) -> ModelMetadataNodeInfo | None:
        """Get enhanced node information."""
        node_info_data = self.root.get("_node_info", {}).get(name)
        if node_info_data:
            return ModelMetadataNodeInfo(**node_info_data)
        return None

    def update_node_info(self, name: str, node_info: ModelMetadataNodeInfo) -> bool:
        """Update node information."""
        if name not in self.root or name.startswith("_"):
            return False

        if "_node_info" not in self.root:
            self.root["_node_info"] = {}

        self.root["_node_info"][name] = node_info.model_dump()
        self._update_analytics()
        return True

    def record_node_usage(
        self,
        name: str,
        success: bool,
        processing_time_ms: float = 0.0,
        error_msg: str | None = None,
    ) -> None:
        """Record node usage for analytics."""
        node_info = self.get_node_info(name)
        if not node_info:
            return

        # Update usage metrics
        metrics = node_info.usage_metrics
        metrics.total_invocations += 1
        metrics.last_used = datetime.now()

        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
            if error_msg:
                metrics.most_recent_error = error_msg

        # Update average processing time
        if processing_time_ms > 0:
            total_time = metrics.avg_processing_time_ms * (
                metrics.total_invocations - 1
            )
            metrics.avg_processing_time_ms = (
                total_time + processing_time_ms
            ) / metrics.total_invocations

        # Calculate popularity score (based on recent usage)
        days_since_last_use = 0
        if metrics.last_used:
            days_since_last_use = (datetime.now() - metrics.last_used).days

        # Popularity decreases over time, increases with usage
        usage_factor = min(metrics.total_invocations / 10.0, 10.0)  # Cap at 10
        recency_factor = max(0, 10 - days_since_last_use)  # Decreases over 10 days
        success_factor = (
            metrics.success_count / max(metrics.total_invocations, 1)
        ) * 10

        metrics.popularity_score = min(
            100.0,
            (usage_factor + recency_factor + success_factor) * 3.33,
        )

        # Update node info
        self.update_node_info(name, node_info)

    def get_nodes_by_type(
        self, node_type: ModelMetadataNodeType
    ) -> dict[str, Union[ModelFunctionNode, dict[str, str]]]:
        """Get all nodes of a specific type."""
        nodes = {}
        for name, node_data in self.root.items():
            if name.startswith("_"):
                continue

            node_info = self.get_node_info(name)
            if node_info and node_info.node_type == node_type:
                nodes[name] = node_data

        return nodes

    def get_nodes_by_status(
        self, status: ModelMetadataNodeStatus
    ) -> dict[str, Union[ModelFunctionNode, dict[str, str]]]:
        """Get all nodes with a specific status."""
        nodes = {}
        for name, node_data in self.root.items():
            if name.startswith("_"):
                continue

            node_info = self.get_node_info(name)
            if node_info and node_info.status == status:
                nodes[name] = node_data

        return nodes

    def get_popular_nodes(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get most popular nodes by usage score."""
        node_scores = []

        for name in self.root:
            if name.startswith("_"):
                continue

            node_info = self.get_node_info(name)
            if node_info:
                node_scores.append((name, node_info.usage_metrics.popularity_score))

        # Sort by popularity score descending
        node_scores.sort(key=lambda x: x[1], reverse=True)
        return node_scores[:limit]

    def deprecate_node(
        self,
        name: str,
        reason: str = "",
        replacement: str | None = None,
    ) -> bool:
        """Mark a node as deprecated."""
        node_info = self.get_node_info(name)
        if not node_info:
            return False

        node_info.status = ModelMetadataNodeStatus.DEPRECATED
        from .model_audit_entry import AuditAction, ModelAuditEntry

        audit_entry = ModelAuditEntry(
            audit_id=f"deprecate_{name}_{datetime.now().timestamp()}",
            action=AuditAction.UPDATE,
            action_detail=f"deprecated: {reason}",
            target_name=name,
            additional_context={"replacement": replacement} if replacement else None,
        )
        node_info.audit_trail.append(audit_entry)

        if replacement:
            node_info.replaces = replacement

        return self.update_node_info(name, node_info)

    def validate_collection(self) -> ModelCollectionValidationResult:
        """Perform comprehensive collection validation."""
        validation_results = ModelCollectionValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            node_validations={},
        )

        for name, node_data in self.root.items():
            if name.startswith("_"):
                continue

            node_validation = ModelNodeValidationResult(
                valid=True,
                errors=[],
                warnings=[],
            )

            # Validate node name
            if not name.isidentifier():
                node_validation.valid = False
                node_validation.errors.append("Invalid node name")

            # Validate node data
            if node_data is None:
                node_validation.valid = False
                node_validation.errors.append("Node data is None")

            # Check for node info
            node_info = self.get_node_info(name)
            if not node_info:
                node_validation.warnings.append("Missing node information")

            # Check for deprecated nodes without replacement
            if node_info and node_info.status == ModelMetadataNodeStatus.DEPRECATED:
                if not node_info.replaces:
                    node_validation.warnings.append(
                        "Deprecated node without replacement",
                    )

            validation_results.node_validations[name] = node_validation

            if not node_validation.valid:
                validation_results.valid = False
                validation_results.errors.extend(node_validation.errors)

            validation_results.warnings.extend(node_validation.warnings)

        return validation_results

    def export_analytics_report(self) -> ModelAnalyticsReport:
        """Export comprehensive analytics report."""
        analytics = self.analytics

        # Calculate additional metrics
        node_infos = []
        for name in self.root:
            if name.startswith("_"):
                continue

            node_info = self.get_node_info(name)
            if node_info:
                node_infos.append(node_info)

        # Performance metrics
        total_invocations = sum(t.usage_metrics.total_invocations for t in node_infos)
        avg_popularity = sum(
            t.usage_metrics.popularity_score for t in node_infos
        ) / max(len(node_infos), 1)

        # Documentation coverage
        documented_nodes = len(
            [t for t in node_infos if t.description or t.documentation],
        )
        doc_coverage = (documented_nodes / max(len(node_infos), 1)) * 100

        return ModelAnalyticsReport(
            collection_metadata=ModelCollectionMetadata(
                id=self.collection_id,
                node_count=self.node_count,
                health_score=self.health_score,
                generated_at=datetime.now().isoformat(),
            ),
            analytics_summary=analytics.model_dump(),
            performance_metrics=ModelPerformanceMetrics(
                total_invocations=total_invocations,
                avg_popularity_score=avg_popularity,
                documentation_coverage=doc_coverage,
            ),
            node_breakdown=ModelNodeBreakdown(
                by_type=analytics.nodes_by_type,
                by_status=analytics.nodes_by_status,
                by_complexity=analytics.nodes_by_complexity,
            ),
            popular_nodes=self.get_popular_nodes(5),
            validation_results=self.validate_collection(),
        )

    def _update_analytics(self) -> None:
        """Internal method to update collection analytics."""
        analytics_data = self.root.get("_metadata_analytics", {})

        # Count nodes by various categories
        nodes_by_type: dict[str, int] = {}
        nodes_by_status: dict[str, int] = {}
        nodes_by_complexity: dict[str, int] = {}
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

        # Update analytics
        analytics_data.update(
            {
                "last_modified": datetime.now().isoformat(),
                "total_nodes": node_count,
                "nodes_by_type": nodes_by_type,
                "nodes_by_status": nodes_by_status,
                "nodes_by_complexity": nodes_by_complexity,
                "total_invocations": total_invocations,
                "overall_success_rate": overall_success_rate,
                "health_score": self.health_score,
            },
        )

        self.root["_metadata_analytics"] = analytics_data

    # Factory methods for common scenarios
    @classmethod
    def create_empty_collection(cls) -> "ModelMetadataNodeCollection":
        """Create an empty metadata node collection."""
        return cls({})

    @classmethod
    def create_from_function_nodes(
        cls,
        nodes_dict: dict[str, ModelFunctionNode],
    ) -> "ModelMetadataNodeCollection":
        """Create collection from existing ModelFunctionNode dictionary."""
        collection = cls(nodes_dict)

        # Add basic node info for each node
        for name, node in nodes_dict.items():
            if hasattr(node, "name") and hasattr(node, "description"):
                node_info = ModelMetadataNodeInfo(
                    name=name,
                    description=getattr(node, "description", ""),
                    node_type=ModelMetadataNodeType.FUNCTION,
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


# Compatibility aliases
MetadataNodeUsageMetrics = ModelMetadataNodeUsageMetrics
MetadataNodeAnalytics = ModelMetadataNodeAnalytics
MetadataNodeInfo = ModelMetadataNodeInfo
MetadataNodeCollection = ModelMetadataNodeCollection
LegacyNodeCollection = ModelMetadataNodeCollection
MetadataNodeComplexity = ModelMetadataNodeComplexity
MetadataNodeStatus = ModelMetadataNodeStatus
MetadataNodeType = ModelMetadataNodeType

# Re-export for current standards
__all__ = [
    "LegacyNodeCollection",
    "MetadataNodeAnalytics",
    "MetadataNodeCollection",
    "MetadataNodeComplexity",
    "MetadataNodeInfo",
    "MetadataNodeStatus",
    "MetadataNodeType",
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    # Compatibility
    "MetadataNodeUsageMetrics",
    "ModelMetadataNodeAnalytics",
    "ModelMetadataNodeCollection",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeUsageMetrics",
]
