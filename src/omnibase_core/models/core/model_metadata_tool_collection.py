"""
Metadata tool collection models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.

# ONEX_EXCLUDE: dict_str_any - RootModel requires dict[str, Any] for heterogeneous collections
# The root dictionary stores: tools (ModelFunctionTool), _metadata_analytics (dict),
# and _tool_info (dict[str, dict]). This heterogeneity necessitates Any type.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import RootModel, computed_field, model_validator

from omnibase_core.enums.enum_audit_action import EnumAuditAction
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata_tool_complexity import EnumMetadataToolComplexity
from omnibase_core.enums.enum_metadata_tool_status import EnumMetadataToolStatus
from omnibase_core.enums.enum_metadata_tool_type import EnumMetadataToolType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.core.model_audit_entry import ModelAuditEntry
from omnibase_core.models.core.model_function_tool import ModelFunctionTool
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_collection_validation import (
    TypedDictCollectionValidation,
)
from omnibase_core.types.typed_dict_metadata_tool_analytics_report import (
    TypedDictMetadataToolAnalyticsReport,
)
from omnibase_core.types.typed_dict_tool_validation import TypedDictToolValidation

from .model_metadata_tool_analytics import ModelMetadataToolAnalytics
from .model_metadata_tool_info import ModelMetadataToolInfo

# Import separated models
from .model_metadata_tool_usage_metrics import ModelMetadataToolUsageMetrics


# ONEX_EXCLUDE: dict_str_any - RootModel heterogeneous collection
class ModelMetadataToolCollection(RootModel[dict[str, Any]]):
    """
    Enterprise-grade collection of metadata/documentation tools for ONEX metadata blocks.

    Enhanced with comprehensive tool analytics, usage tracking, performance monitoring,
    and operational insights for documentation and metadata management systems.

    Note: Uses dict[str, Any] for root because this collection is heterogeneous,
    containing tools (ModelFunctionTool), metadata analytics (dict), and tool info (dict).
    """

    # ONEX_EXCLUDE: dict_str_any - Constructor accepts heterogeneous dict input
    def __init__(
        self,
        root: dict[str, Any] | ModelMetadataToolCollection | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with enhanced enterprise features."""
        if root is None:
            root = {}
        elif isinstance(root, ModelMetadataToolCollection):
            root = root.root

        # Initialize the root dictionary
        super().__init__(root)

        # Initialize enterprise features if not present
        if "_metadata_analytics" not in self.root:
            self.root["_metadata_analytics"] = ModelMetadataToolAnalytics(
                collection_created=datetime.now(),
                last_modified=datetime.now(),
                total_tools=0,
                tools_by_type={},
                tools_by_status={},
                tools_by_complexity={},
                total_invocations=0,
                overall_success_rate=100.0,
                avg_collection_performance=0.0,
                health_score=100.0,
                documentation_coverage=0.0,
                validation_compliance=100.0,
            ).model_dump()

        if "_tool_info" not in self.root:
            self.root["_tool_info"] = {}

    @model_validator(mode="before")
    @classmethod
    def coerce_tool_values(cls, data: Any) -> Any:
        """Enhanced tool value coercion with validation and enhancement."""
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                # Skip enterprise metadata fields
                if k.startswith(("_metadata_", "_tool_")):
                    new_data[k] = v
                    continue

                if isinstance(v, dict):
                    # Enhanced ModelFunctionTool creation with validation
                    try:
                        function_tool = ModelFunctionTool.model_validate(
                            v
                        )  # Pydantic model_validate for loosely-typed dict input
                        new_data[k] = function_tool
                    except PYDANTIC_MODEL_ERRORS:
                        # fallback-ok: Fallback to raw dictionary if ModelFunctionTool creation fails
                        new_data[k] = v
                else:
                    new_data[k] = v
            return new_data

        if isinstance(data, ModelMetadataToolCollection):
            return data.root

        return data or {}

    @model_validator(mode="after")
    def check_function_names_and_enhance(self) -> ModelMetadataToolCollection:
        """Enhanced validation with analytics updates."""
        tool_count = 0
        tools_by_type: dict[str, int] = {}
        tools_by_status: dict[str, int] = {}
        tools_by_complexity: dict[str, int] = {}

        for name, _tool_data in self.root.items():
            # Skip enterprise metadata fields
            if name.startswith(("_metadata_", "_tool_")):
                continue

            # Validate function name
            if not name.isidentifier():
                msg = f"Invalid function name: {name}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

            tool_count += 1

            # Update analytics if tool info exists
            if name in self.root.get("_tool_info", {}):
                tool_info = self.root["_tool_info"][name]
                if isinstance(tool_info, dict):
                    tool_type = tool_info.get("tool_type", "function")
                    tool_status = tool_info.get("status", "active")
                    tool_complexity = tool_info.get("complexity", "simple")

                    tools_by_type[tool_type] = tools_by_type.get(tool_type, 0) + 1
                    tools_by_status[tool_status] = (
                        tools_by_status.get(tool_status, 0) + 1
                    )
                    tools_by_complexity[tool_complexity] = (
                        tools_by_complexity.get(tool_complexity, 0) + 1
                    )

        # Update analytics
        analytics = self.root.get("_metadata_analytics", {})
        analytics.update(
            {
                "last_modified": datetime.now().isoformat(),
                "total_tools": tool_count,
                "tools_by_type": tools_by_type,
                "tools_by_status": tools_by_status,
                "tools_by_complexity": tools_by_complexity,
            },
        )
        self.root["_metadata_analytics"] = analytics

        return self

    # NOTE(OMN-1302): Pydantic @computed_field decorator - mypy doesn't understand Pydantic property semantics.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def collection_id(self) -> str:
        """Generate unique identifier for this collection."""
        tool_names = sorted([k for k in self.root if not k.startswith("_")])
        content = f"metadata_tools:{':'.join(tool_names)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # NOTE(OMN-1302): Pydantic @computed_field decorator - mypy doesn't understand Pydantic property semantics.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def tool_count(self) -> int:
        """Get total number of tools (excluding metadata)."""
        return len([k for k in self.root if not k.startswith("_")])

    # NOTE(OMN-1302): Pydantic @computed_field decorator - mypy doesn't understand Pydantic property semantics.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def analytics(self) -> ModelMetadataToolAnalytics:
        """Get collection analytics."""
        analytics_data = self.root.get("_metadata_analytics", {})
        return ModelMetadataToolAnalytics(**analytics_data)

    # NOTE(OMN-1302): Pydantic @computed_field decorator - mypy doesn't understand Pydantic property semantics.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def health_score(self) -> float:
        """Calculate overall collection health score."""
        if self.tool_count == 0:
            return 100.0

        analytics = self.analytics

        # Base score from success rate
        base_score = analytics.overall_success_rate

        # Penalty for deprecated/disabled tools
        deprecated_ratio = analytics.tools_by_status.get("deprecated", 0) / max(
            analytics.total_tools,
            1,
        )
        disabled_ratio = analytics.tools_by_status.get("disabled", 0) / max(
            analytics.total_tools,
            1,
        )

        penalty = (deprecated_ratio + disabled_ratio) * 20  # Up to 20 point penalty

        # Bonus for good documentation coverage
        doc_bonus = analytics.documentation_coverage * 0.1  # Up to 10 point bonus

        return max(0.0, min(100.0, base_score - penalty + doc_bonus))

    def add_tool(
        self,
        name: str,
        tool_data: ModelFunctionTool | dict[str, object],
        tool_info: ModelMetadataToolInfo | None = None,
    ) -> bool:
        """
        Add a tool to the collection with enhanced metadata tracking.

        Args:
            name: Tool name
            tool_data: Tool data (ModelFunctionTool, dictionary, etc.)
            tool_info: Optional enhanced tool information

        Returns:
            bool: True if tool added successfully
        """
        try:
            # Validate tool name
            if not name.isidentifier():
                return False

            # Add the tool data
            if isinstance(tool_data, dict):
                try:
                    self.root[name] = ModelFunctionTool.model_validate(
                        tool_data
                    )  # Pydantic model_validate for loosely-typed dict input
                except PYDANTIC_MODEL_ERRORS:
                    # fallback-ok: Fallback to raw dict if ModelFunctionTool creation fails
                    self.root[name] = tool_data
            else:
                self.root[name] = tool_data

            # Add tool info if provided
            if tool_info:
                if "_tool_info" not in self.root:
                    self.root["_tool_info"] = {}
                self.root["_tool_info"][name] = tool_info.model_dump()
            elif name not in self.root.get("_tool_info", {}):
                # Create default tool info

                default_info = ModelMetadataToolInfo(
                    name=name,
                    tool_type=EnumMetadataToolType.FUNCTION,
                    status=EnumMetadataToolStatus.ACTIVE,
                    complexity=EnumMetadataToolComplexity.SIMPLE,
                    description="",
                    documentation="",
                    author="Unknown",
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    security_level="standard",
                    replaces=None,
                )
                if "_tool_info" not in self.root:
                    self.root["_tool_info"] = {}
                self.root["_tool_info"][name] = default_info.model_dump()

            # Update analytics
            self._update_analytics()

            return True

        except (
            Exception
        ):  # fallback-ok: registration method, False indicates registration failure
            return False

    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the collection."""
        if name in self.root and not name.startswith("_"):
            del self.root[name]

            # Remove tool info if exists
            if "_tool_info" in self.root and name in self.root["_tool_info"]:
                del self.root["_tool_info"][name]

            # Update analytics
            self._update_analytics()
            return True

        return False

    def get_tool(self, name: str) -> ModelFunctionTool | dict[str, object] | None:
        """Get a tool by name."""
        return self.root.get(name)

    def get_tool_info(self, name: str) -> ModelMetadataToolInfo | None:
        """Get enhanced tool information."""
        tool_info_data = self.root.get("_tool_info", {}).get(name)
        if tool_info_data:
            return ModelMetadataToolInfo(**tool_info_data)
        return None

    def update_tool_info(self, name: str, tool_info: ModelMetadataToolInfo) -> bool:
        """Update tool information."""
        if name not in self.root or name.startswith("_"):
            return False

        if "_tool_info" not in self.root:
            self.root["_tool_info"] = {}

        self.root["_tool_info"][name] = tool_info.model_dump()
        self._update_analytics()
        return True

    def record_tool_usage(
        self,
        name: str,
        success: bool,
        processing_time_ms: float = 0.0,
        error_msg: str | None = None,
    ) -> None:
        """Record tool usage for analytics."""
        tool_info = self.get_tool_info(name)
        if not tool_info:
            return

        # Update usage metrics
        metrics = tool_info.usage_metrics
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

        # Update tool info
        self.update_tool_info(name, tool_info)

    def get_tools_by_type(
        self, tool_type: EnumMetadataToolType
    ) -> dict[str, ModelFunctionTool | dict[str, object]]:
        """Get all tools of a specific type."""
        # Tool data values can be ModelFunctionTool or raw dict
        tools: dict[str, ModelFunctionTool | dict[str, object]] = {}
        for name, tool_data in self.root.items():
            if name.startswith("_"):
                continue

            tool_info = self.get_tool_info(name)
            if tool_info and tool_info.tool_type == tool_type:
                # Cast to ToolDataType - tool entries are either ModelFunctionTool or SerializedDict
                if isinstance(tool_data, (ModelFunctionTool, dict)):
                    tools[name] = tool_data

        return tools

    def get_tools_by_status(
        self, status: EnumMetadataToolStatus
    ) -> dict[str, ModelFunctionTool | dict[str, object]]:
        """Get all tools with a specific status."""
        # Tool data values can be ModelFunctionTool or raw dict
        tools: dict[str, ModelFunctionTool | dict[str, object]] = {}
        for name, tool_data in self.root.items():
            if name.startswith("_"):
                continue

            tool_info = self.get_tool_info(name)
            if tool_info and tool_info.status == status:
                # Cast to ToolDataType - tool entries are either ModelFunctionTool or SerializedDict
                if isinstance(tool_data, (ModelFunctionTool, dict)):
                    tools[name] = tool_data

        return tools

    def get_popular_tools(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get most popular tools by usage score."""
        tool_scores = []

        for name in self.root:
            if name.startswith("_"):
                continue

            tool_info = self.get_tool_info(name)
            if tool_info:
                tool_scores.append((name, tool_info.usage_metrics.popularity_score))

        # Sort by popularity score descending
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        return tool_scores[:limit]

    def deprecate_tool(
        self,
        name: str,
        reason: str = "",
        replacement: str | None = None,
    ) -> bool:
        """Mark a tool as deprecated."""
        tool_info = self.get_tool_info(name)
        if not tool_info:
            return False

        from uuid import NAMESPACE_DNS, uuid5

        tool_info.status = EnumMetadataToolStatus.DEPRECATED
        # Generate deterministic UUID for audit entry
        audit_id = uuid5(
            NAMESPACE_DNS, f"deprecate_{name}_{datetime.now().isoformat()}"
        )
        # Generate target_id properly - tools don't have UUIDs, so use None or empty string
        target_id = UUID(int=0) if not name else None  # Use null UUID or None
        tool_info.audit_trail.append(
            ModelAuditEntry(
                audit_id=audit_id,
                timestamp=datetime.now(),
                action=EnumAuditAction.UPDATE,
                action_detail=f"Deprecated tool: {reason}",
                target_type="tool",
                target_id=target_id,
                success=True,
                additional_context={
                    "reason": reason,
                    "replacement": replacement or "",
                },
            )
        )

        if replacement:
            tool_info.replaces = replacement

        return self.update_tool_info(name, tool_info)

    def validate_collection(self) -> TypedDictCollectionValidation:
        """Perform comprehensive collection validation."""
        tool_validations: dict[str, TypedDictToolValidation] = {}
        all_errors: list[str] = []
        all_warnings: list[str] = []
        is_valid = True

        for name, tool_data in self.root.items():
            if name.startswith("_"):
                continue

            tool_errors: list[str] = []
            tool_warnings: list[str] = []
            tool_is_valid = True

            # Validate tool name
            if not name.isidentifier():
                tool_is_valid = False
                tool_errors.append("Invalid tool name")

            # Validate tool data
            if tool_data is None:
                tool_is_valid = False
                tool_errors.append("Tool data is None")

            # Check for tool info
            tool_info = self.get_tool_info(name)
            if not tool_info:
                tool_warnings.append("Missing tool information")

            # Check for deprecated tools without replacement
            if tool_info and tool_info.status == EnumMetadataToolStatus.DEPRECATED:
                if not tool_info.replaces:
                    tool_warnings.append(
                        "Deprecated tool without replacement",
                    )

            tool_validations[name] = TypedDictToolValidation(
                valid=tool_is_valid,
                errors=tool_errors,
                warnings=tool_warnings,
            )

            if not tool_is_valid:
                is_valid = False
                all_errors.extend(tool_errors)

            all_warnings.extend(tool_warnings)

        return TypedDictCollectionValidation(
            valid=is_valid,
            errors=all_errors,
            warnings=all_warnings,
            tool_validations=tool_validations,
        )

    def export_analytics_report(self) -> TypedDictMetadataToolAnalyticsReport:
        """Export comprehensive analytics report."""
        analytics = self.analytics

        # Calculate additional metrics
        tool_infos: list[ModelMetadataToolInfo] = []
        for name in self.root:
            if name.startswith("_"):
                continue

            tool_info = self.get_tool_info(name)
            if tool_info:
                tool_infos.append(tool_info)

        # Performance metrics
        total_invocations = sum(t.usage_metrics.total_invocations for t in tool_infos)
        avg_popularity = sum(
            t.usage_metrics.popularity_score for t in tool_infos
        ) / max(len(tool_infos), 1)

        # Documentation coverage
        documented_tools = len(
            [t for t in tool_infos if t.description or t.documentation]
        )
        doc_coverage = (documented_tools / max(len(tool_infos), 1)) * 100

        # Build the analytics summary data with proper typing
        analytics_dump = analytics.model_dump()

        return TypedDictMetadataToolAnalyticsReport(
            collection_metadata={
                "id": self.collection_id,
                "tool_count": self.tool_count,
                "health_score": self.health_score,
                "generated_at": datetime.now().isoformat(),
            },
            analytics_summary={
                "collection_created": str(analytics_dump.get("collection_created", "")),
                "last_modified": str(analytics_dump.get("last_modified", "")),
                "total_tools": int(analytics_dump.get("total_tools", 0)),
                "tools_by_type": dict(analytics_dump.get("tools_by_type", {})),
                "tools_by_status": dict(analytics_dump.get("tools_by_status", {})),
                "tools_by_complexity": dict(
                    analytics_dump.get("tools_by_complexity", {})
                ),
                "total_invocations": int(analytics_dump.get("total_invocations", 0)),
                "overall_success_rate": float(
                    analytics_dump.get("overall_success_rate", 100.0)
                ),
                "avg_collection_performance": float(
                    analytics_dump.get("avg_collection_performance", 0.0)
                ),
                "health_score": float(analytics_dump.get("health_score", 100.0)),
                "documentation_coverage": float(
                    analytics_dump.get("documentation_coverage", 0.0)
                ),
                "validation_compliance": float(
                    analytics_dump.get("validation_compliance", 100.0)
                ),
            },
            performance_metrics={
                "total_invocations": total_invocations,
                "avg_popularity_score": avg_popularity,
                "documentation_coverage": doc_coverage,
            },
            tool_breakdown={
                "by_type": analytics.tools_by_type,
                "by_status": analytics.tools_by_status,
                "by_complexity": analytics.tools_by_complexity,
            },
            popular_tools=self.get_popular_tools(5),
            validation_results=self.validate_collection(),
        )

    def _update_analytics(self) -> None:
        """Internal method to update collection analytics."""
        analytics_data = self.root.get("_metadata_analytics", {})

        # Count tools by various categories
        tools_by_type: dict[str, int] = {}
        tools_by_status: dict[str, int] = {}
        tools_by_complexity: dict[str, int] = {}
        total_invocations = 0
        total_success = 0

        tool_count = 0
        for name in self.root:
            if name.startswith("_"):
                continue

            tool_count += 1
            tool_info = self.get_tool_info(name)
            if tool_info:
                # Count by categories
                tools_by_type[tool_info.tool_type.value] = (
                    tools_by_type.get(tool_info.tool_type.value, 0) + 1
                )
                tools_by_status[tool_info.status.value] = (
                    tools_by_status.get(tool_info.status.value, 0) + 1
                )
                tools_by_complexity[tool_info.complexity.value] = (
                    tools_by_complexity.get(tool_info.complexity.value, 0) + 1
                )

                # Aggregate usage metrics
                total_invocations += tool_info.usage_metrics.total_invocations
                total_success += tool_info.usage_metrics.success_count

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
                "total_tools": tool_count,
                "tools_by_type": tools_by_type,
                "tools_by_status": tools_by_status,
                "tools_by_complexity": tools_by_complexity,
                "total_invocations": total_invocations,
                "overall_success_rate": overall_success_rate,
                "health_score": self.health_score,
            },
        )

        self.root["_metadata_analytics"] = analytics_data

    # Factory methods for common scenarios
    @classmethod
    def create_empty_collection(cls) -> ModelMetadataToolCollection:
        """Create an empty metadata tool collection."""
        return cls({})

    @classmethod
    def create_from_function_tools(
        cls,
        tools_dict: dict[str, ModelFunctionTool],
    ) -> ModelMetadataToolCollection:
        """Create collection from existing ModelFunctionTool dictionary."""
        collection = cls(tools_dict)

        # Add basic tool info for each tool

        for name, tool in tools_dict.items():
            if hasattr(tool, "name") and hasattr(tool, "description"):
                tool_info = ModelMetadataToolInfo(
                    name=name,
                    description=getattr(tool, "description", ""),
                    tool_type=EnumMetadataToolType.FUNCTION,
                    status=EnumMetadataToolStatus.ACTIVE,
                    complexity=EnumMetadataToolComplexity.SIMPLE,
                    documentation="",
                    author="Unknown",
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    security_level="standard",
                    replaces=None,
                )
                collection.update_tool_info(name, tool_info)

        return collection

    @classmethod
    def create_documentation_collection(
        cls,
        name: str = "documentation",
    ) -> ModelMetadataToolCollection:
        """Create a collection optimized for documentation tools."""
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
MetadataToolUsageMetrics = ModelMetadataToolUsageMetrics
MetadataToolAnalytics = ModelMetadataToolAnalytics
MetadataToolInfo = ModelMetadataToolInfo
MetadataToolCollection = ModelMetadataToolCollection
LegacyToolCollection = ModelMetadataToolCollection

# Re-export for current standards
__all__ = [
    "EnumMetadataToolComplexity",
    "EnumMetadataToolStatus",
    "EnumMetadataToolType",
    "LegacyToolCollection",
    "MetadataToolAnalytics",
    "MetadataToolCollection",
    "MetadataToolInfo",
    "MetadataToolUsageMetrics",
    "ModelMetadataToolAnalytics",
    "ModelMetadataToolCollection",
    "ModelMetadataToolInfo",
    "ModelMetadataToolUsageMetrics",
]
