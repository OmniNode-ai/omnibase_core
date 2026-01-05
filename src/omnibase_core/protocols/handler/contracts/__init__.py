"""
Handler contract protocols for ONEX Core.

This package contains protocol definitions for handler contracts, including:
- ProtocolHandlerContract: Main handler contract interface
- ProtocolHandlerBehaviorDescriptor: Handler behavior characteristics
- ProtocolCapabilityDependency: Capability requirements
- ProtocolExecutionConstraints: Runtime constraints
- ProtocolExecutionConstrainable: Mixin for constraint declaration

These protocols were migrated from omnibase_spi to omnibase_core to support
the dependency direction: SPI → Core (allowed), Core → SPI (forbidden).

See Also:
    - ModelHandlerContract (OMN-1117): Pydantic implementation of these protocols
    - docs/architecture/HANDLER_PROTOCOL_DRIVEN_ARCHITECTURE.md
"""

from omnibase_core.protocols.handler.contracts.protocol_capability_dependency import (
    ProtocolCapabilityDependency,
)
from omnibase_core.protocols.handler.contracts.protocol_execution_constrainable import (
    ProtocolExecutionConstrainable,
)
from omnibase_core.protocols.handler.contracts.protocol_execution_constraints import (
    ProtocolExecutionConstraints,
)
from omnibase_core.protocols.handler.contracts.protocol_handler_behavior_descriptor import (
    ProtocolHandlerBehaviorDescriptor,
)
from omnibase_core.protocols.handler.contracts.protocol_handler_contract import (
    ProtocolHandlerContract,
)

__all__ = [
    "ProtocolCapabilityDependency",
    "ProtocolExecutionConstrainable",
    "ProtocolExecutionConstraints",
    "ProtocolHandlerBehaviorDescriptor",
    "ProtocolHandlerContract",
]
