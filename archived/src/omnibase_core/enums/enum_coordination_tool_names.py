"""
Enum for coordination tool names.
Single responsibility: Centralized coordination tool name definitions.
"""

from enum import Enum


class EnumCoordinationToolNames(str, Enum):
    """Coordination tool names following ONEX enum-backed naming standards."""

    TOOL_GENERIC_HUB_NODE = "tool_generic_hub_node"
    TOOL_CONTRACT_EVENT_ROUTER = "tool_contract_event_router"
    TOOL_COMPOSITION_COORDINATOR = "tool_composition_coordinator"
    TOOL_SUBWORKFLOW_EXECUTOR = "tool_subworkflow_executor"
    TOOL_COMPOSITION_ORCHESTRATOR = "tool_composition_orchestrator"
    TOOL_WORKFLOW_REGISTRY = "tool_workflow_registry"
