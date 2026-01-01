"""
Logging protocols for ONEX logging infrastructure.

This module provides protocol definitions for logging formatters and output handlers
used by the ONEX logging system.
"""

from omnibase_core.protocols.logging.protocol_minimal_logger import (
    ProtocolMinimalLogger,
)
from omnibase_core.protocols.logging.protocol_registry_node import (
    ProtocolRegistryNode,
)
from omnibase_core.protocols.logging.protocol_smart_log_formatter import (
    ProtocolSmartLogFormatter,
)
from omnibase_core.protocols.protocol_context_aware_output_handler import (
    ProtocolContextAwareOutputHandler,
)

__all__ = [
    "ProtocolContextAwareOutputHandler",
    "ProtocolMinimalLogger",
    "ProtocolRegistryNode",
    "ProtocolSmartLogFormatter",
]
