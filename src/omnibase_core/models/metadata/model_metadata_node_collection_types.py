"""
TypedDict definitions for ModelMetadataNodeCollection.

Provides strict typing for structured data used in metadata node collections.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import NotRequired, TypedDict

from typing_extensions import Required


class NodeInfoData(TypedDict):
    """TypedDict for node information data structure."""

    name: Required[str]
    description: NotRequired[str]
    node_type: NotRequired[str]
    status: NotRequired[str]
    complexity: NotRequired[str]
    version: NotRequired[str]
    created_at: NotRequired[str]
    updated_at: NotRequired[str]
    last_validated: NotRequired[str | None]
    tags: NotRequired[list[str]]
    categories: NotRequired[list[str]]
    has_documentation: NotRequired[bool]
    has_examples: NotRequired[bool]
    documentation_quality: NotRequired[str]
    dependencies: NotRequired[list[str]]
    related_nodes: NotRequired[list[str]]
    usage_metrics: NotRequired[dict[str, str | int | float]]
    custom_metadata: NotRequired[dict[str, str | int | bool | float]]


class AnalyticsData(TypedDict):
    """TypedDict for analytics data structure."""

    collection_name: NotRequired[str]
    collection_purpose: NotRequired[str]
    collection_created: NotRequired[str]
    last_modified: Required[str]
    total_nodes: NotRequired[int]
    nodes_by_type: NotRequired[dict[str, int]]
    nodes_by_status: NotRequired[dict[str, int]]
    nodes_by_complexity: NotRequired[dict[str, int]]
    total_invocations: NotRequired[int]
    overall_success_rate: NotRequired[float]
    health_score: NotRequired[float]
    documentation_coverage: NotRequired[float]
    average_execution_time_ms: NotRequired[float]
    peak_memory_usage_mb: NotRequired[float]
    error_count: NotRequired[int]
    warning_count: NotRequired[int]
    critical_error_count: NotRequired[int]
    custom_metrics: NotRequired[dict[str, str | int | bool | float]]


# NodeInfoContainer is a regular dict since TypedDict cannot handle dynamic keys
NodeInfoContainer = dict[str, NodeInfoData]


# Import the clean model replacement
from .model_function_node_data import ModelFunctionNodeData

# Clean replacement for the horrible union type
FunctionNodeData = ModelFunctionNodeData


# Export for use
__all__ = [
    "AnalyticsData",
    "FunctionNodeData",
    "ModelFunctionNodeData",
    "NodeInfoContainer",
    "NodeInfoData",
]
