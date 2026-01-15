"""
Runtime protocols for ONEX EnvelopeRouter and handler integration.

This module provides Core-native protocol definitions for runtime handlers.
These protocols establish the contracts that handler implementations (in SPI
or other packages) must satisfy, enabling dependency inversion.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Use TYPE_CHECKING imports to avoid runtime dependency cycles
- Provide complete type hints for mypy strict mode compliance

Module Organization:
- protocol_handler.py: Handler protocol for ONEX runtime handler interface
- protocol_handler_registry.py: Handler registry protocol for DI abstraction
- protocol_message_handler.py: Category-based message handler protocol

Usage:
    from omnibase_core.protocols.runtime import ProtocolHandler, ProtocolMessageHandler

    class MyHandler(ProtocolHandler):
        @property
        def handler_type(self) -> EnumHandlerType:
            return EnumHandlerType.HTTP

        async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            # Handler implementation
            ...

        def describe(self) -> TypedDictHandlerMetadata:
            return {"name": "my_handler", "version": ModelSemVer(major=1, minor=0, patch=0)}

Dependency Injection:
    Register handler registry under "ProtocolHandlerRegistry" DI token:

    .. code-block:: python

        container.register_service("ProtocolHandlerRegistry", registry)

    Resolve via DI in node constructors:

    .. code-block:: python

        registry = container.get_service("ProtocolHandlerRegistry")

Related:
    - OMN-226: ProtocolHandler interface definition
    - OMN-228: EnvelopeRouter transport-agnostic orchestrator
    - OMN-934: Handler registry for message dispatch engine
    - OMN-1293: Contract-driven handler routing

.. versionadded:: 0.4.0
.. versionchanged:: 0.6.3
   Added ProtocolHandlerRegistry for handler registry abstraction.
"""

from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler
from omnibase_core.protocols.runtime.protocol_handler_registry import (
    ProtocolHandlerRegistry,
)
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)

__all__ = ["ProtocolHandler", "ProtocolHandlerRegistry", "ProtocolMessageHandler"]
