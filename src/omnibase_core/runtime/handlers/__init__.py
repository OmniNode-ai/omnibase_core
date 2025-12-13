"""
ONEX Runtime Handlers Package.

This package contains handler implementations for the ONEX runtime.
Handlers are execution units that process ModelOnexEnvelope instances
for different types of I/O operations.

Available Handlers:
    - HandlerLocal: Dev/test echo handler (NOT for production use)

Related:
    - OMN-230: HandlerLocal implementation
    - ProtocolHandler: Protocol interface for handlers

.. versionadded:: 0.4.0
"""

from omnibase_core.runtime.handlers.handler_local import HandlerLocal

__all__ = ["HandlerLocal"]
