"""Handler protocols for message dispatch.

This package contains protocols for handler execution context, contracts,
and related handler infrastructure.

Subpackages:
    - contracts: Handler contract protocols (ProtocolHandlerContract, etc.)
"""

from omnibase_core.protocols.handler.contracts import (
    ProtocolCapabilityDependency,
    ProtocolExecutionConstrainable,
    ProtocolExecutionConstraints,
    ProtocolHandlerBehaviorDescriptor,
    ProtocolHandlerContract,
)
from omnibase_core.protocols.handler.protocol_handler_context import (
    ProtocolHandlerContext,
)

__all__ = [
    # Handler Context
    "ProtocolHandlerContext",
    # Handler Contracts (OMN-1164)
    "ProtocolCapabilityDependency",
    "ProtocolExecutionConstrainable",
    "ProtocolExecutionConstraints",
    "ProtocolHandlerBehaviorDescriptor",
    "ProtocolHandlerContract",
]
