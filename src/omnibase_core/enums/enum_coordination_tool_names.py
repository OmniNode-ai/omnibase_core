"""
Enum for coordination tool names.
Single responsibility: Centralized coordination tool name definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCoordinationToolNames(StrValueHelper, str, Enum):
    """Coordination tool names following ONEX enum-backed naming standards."""

    TOOL_GENERIC_HUB_NODE = "tool_generic_hub_node"
    TOOL_CONTRACT_EVENT_ROUTER = "tool_contract_event_router"
    TOOL_COMPOSITION_COORDINATOR = "tool_composition_coordinator"
    TOOL_SUBWORKFLOW_EXECUTOR = "tool_subworkflow_executor"
    TOOL_COMPOSITION_ORCHESTRATOR = "tool_composition_orchestrator"
    TOOL_WORKFLOW_REGISTRY = "tool_workflow_registry"


__all__ = ["EnumCoordinationToolNames"]
