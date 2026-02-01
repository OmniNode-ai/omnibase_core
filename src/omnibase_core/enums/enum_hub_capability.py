#!/usr/bin/env python3
"""
Hub Capability Enum.

Strongly-typed enum for hub capability types for different domains.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHubCapability(StrValueHelper, str, Enum):
    """Hub capability types for different domains."""

    # Core hub capabilities
    TOOL_EXECUTION = "tool_execution"
    WORKFLOW_EXECUTION = "workflow_execution"
    EVENT_ROUTING = "event_routing"
    STATE_MANAGEMENT = "state_management"
    REMOTE_TOOLS = "remote_tools"
    HEALTH_MONITORING = "health_monitoring"
    PERFORMANCE_METRICS = "performance_metrics"
    EVENT_BUS_INTEGRATION = "event_bus_integration"

    # AI domain capabilities
    AI_TOOL_REGISTRY = "ai_tool_registry"
    TOOL_DISCOVERY = "tool_discovery"
    MCP_SERVER_INTEGRATION = "mcp_server_integration"

    # Canary domain capabilities
    CANARY_DEPLOYMENT = "canary_deployment"
    TESTING_ORCHESTRATION = "testing_orchestration"
    VALIDATION_WORKFLOWS = "validation_workflows"
    PROGRESSIVE_ROLLOUTS = "progressive_rollouts"
    ROLLBACK_AUTOMATION = "rollback_automation"


__all__ = ["EnumHubCapability"]
