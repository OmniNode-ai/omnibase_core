"""
ONEX Runtime Module.

This module provides runtime infrastructure for ONEX node execution,
including node instance management and execution coordination.

Components:
    - RuntimeNodeInstance: Lightweight wrapper for node execution that delegates
      to NodeRuntime for actual envelope processing.
    - NodeInstance: Alias for RuntimeNodeInstance
    - ProtocolNodeRuntime: Protocol for runtime implementations

Architecture:
    The runtime module follows the ONEX delegation pattern where:
    - RuntimeNodeInstance handles lifecycle (initialize/shutdown) and envelope reception
    - NodeRuntime (to be implemented) handles actual execution with proper
      handler dispatch, error handling, and observability

This separation ensures:
    - Clean separation of concerns
    - No I/O code in RuntimeNodeInstance (pure coordination)
    - Testability through protocol-based dependencies
    - Future extensibility for different runtime implementations
"""

from omnibase_core.runtime.protocol_node_runtime import ProtocolNodeRuntime
from omnibase_core.runtime.runtime_node_instance import (
    NodeInstance,
    RuntimeNodeInstance,
)

__all__ = ["RuntimeNodeInstance", "NodeInstance", "ProtocolNodeRuntime"]
