"""
Core-native type protocols.

This module provides protocol definitions for common type constraints
and behaviors used across Core. These are Core-native equivalents of
the SPI type protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Marker protocols: Use Literal[True] markers for runtime checks
- Minimal interfaces: Only define what Core actually needs
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from omnibase_core.protocols.types.protocol_action import ProtocolAction

# Node Protocols (OMN-662)
from omnibase_core.protocols.types.protocol_compute import ProtocolCompute
from omnibase_core.protocols.types.protocol_configurable import ProtocolConfigurable
from omnibase_core.protocols.types.protocol_effect import ProtocolEffect
from omnibase_core.protocols.types.protocol_executable import ProtocolExecutable
from omnibase_core.protocols.types.protocol_identifiable import ProtocolIdentifiable
from omnibase_core.protocols.types.protocol_log_emitter import ProtocolLogEmitter
from omnibase_core.protocols.types.protocol_metadata import ProtocolMetadata
from omnibase_core.protocols.types.protocol_metadata_provider import (
    ProtocolMetadataProvider,
)
from omnibase_core.protocols.types.protocol_nameable import ProtocolNameable
from omnibase_core.protocols.types.protocol_node_metadata import ProtocolNodeMetadata
from omnibase_core.protocols.types.protocol_node_metadata_block import (
    ProtocolNodeMetadataBlock,
)
from omnibase_core.protocols.types.protocol_node_result import ProtocolNodeResult
from omnibase_core.protocols.types.protocol_orchestrator import ProtocolOrchestrator
from omnibase_core.protocols.types.protocol_schema_value import ProtocolSchemaValue
from omnibase_core.protocols.types.protocol_serializable import ProtocolSerializable
from omnibase_core.protocols.types.protocol_service_instance import (
    ProtocolServiceInstance,
)
from omnibase_core.protocols.types.protocol_service_metadata import (
    ProtocolServiceMetadata,
)
from omnibase_core.protocols.types.protocol_state import ProtocolState
from omnibase_core.protocols.types.protocol_supported_metadata_type import (
    ProtocolSupportedMetadataType,
)
from omnibase_core.protocols.types.protocol_validatable import ProtocolValidatable
from omnibase_core.protocols.types.protocol_workflow_reducer import (
    ProtocolWorkflowReducer,
)

__all__ = [
    # Marker Protocols
    "ProtocolIdentifiable",
    "ProtocolNameable",
    "ProtocolConfigurable",
    "ProtocolExecutable",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    "ProtocolSerializable",
    "ProtocolLogEmitter",
    "ProtocolSupportedMetadataType",
    # Schema
    "ProtocolSchemaValue",
    # Node Metadata
    "ProtocolNodeMetadataBlock",
    "ProtocolNodeMetadata",
    # Action and Result
    "ProtocolAction",
    "ProtocolNodeResult",
    # Workflow Reducer
    "ProtocolWorkflowReducer",
    # Node Protocols (ONEX Four-Node Architecture)
    "ProtocolCompute",
    "ProtocolEffect",
    "ProtocolOrchestrator",
    # State
    "ProtocolState",
    "ProtocolMetadata",
    # Service
    "ProtocolServiceInstance",
    "ProtocolServiceMetadata",
]
