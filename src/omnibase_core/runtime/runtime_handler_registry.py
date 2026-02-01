"""
Handler Registry - Module re-exports.

This module re-exports ProtocolMessageHandler and ServiceHandlerRegistry from
their canonical locations for convenience.

Canonical Locations:
    - ProtocolMessageHandler: omnibase_core.protocols.runtime.protocol_message_handler
    - ServiceHandlerRegistry: omnibase_core.services.service_handler_registry

Import Patterns:
    .. code-block:: python

        # Preferred - import from canonical locations
        from omnibase_core.protocols.runtime import ProtocolMessageHandler
        from omnibase_core.services import ServiceHandlerRegistry

        # Also available from this module
        from omnibase_core.runtime.runtime_handler_registry import (
            ProtocolMessageHandler,
            ServiceHandlerRegistry,
        )

Related:
    - OMN-934: Handler registry for message dispatch engine
    - OMN-941: Standardize handler output model

.. versionadded:: 0.4.0
"""

from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.services.service_handler_registry import ServiceHandlerRegistry

__all__ = [
    "ProtocolMessageHandler",
    "ServiceHandlerRegistry",
]
