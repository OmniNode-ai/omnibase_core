# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-12-11T00:00:00.000000'
# description: TypedDict for tool performance summary data
# entrypoint: python://typed_dict_tool_performance_summary
# hash: auto-generated
# last_modified_at: '2025-12-11T00:00:00.000000'
# lifecycle: active
# meta_type: type
# metadata_version: 0.1.0
# name: typed_dict_tool_performance_summary.py
# namespace: python://omnibase.types.typed_dict_tool_performance_summary
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: auto-generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
TypedDict for Tool Performance Summary.

This module defines the TypedDictToolPerformanceSummary TypedDict used to
represent performance metrics for tool execution in a structured format.
"""

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.models.discovery.model_resource_usage import ModelResourceUsage


class TypedDictToolPerformanceSummary(TypedDict, total=False):
    """Performance summary for tool execution.

    Required fields:
        execution_time_ms: Total execution time in milliseconds.
        priority: Execution priority level.
        mode: Execution mode (synchronous/asynchronous).

    Optional fields:
        queue_time_ms: Time spent in queue before execution.
        total_time_ms: Total time including queue time.
        resource_usage: Resource usage during execution.
    """

    execution_time_ms: int
    priority: str
    mode: str
    queue_time_ms: int
    total_time_ms: int
    resource_usage: "ModelResourceUsage"
