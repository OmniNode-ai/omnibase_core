"""
Event sink implementations for contract validation.

This package provides sink implementations for routing contract validation
events to different destinations (memory, file, kafka).

.. versionadded:: 0.4.0
"""

from omnibase_core.services.sinks.service_sink_file import ServiceFileSink
from omnibase_core.services.sinks.service_sink_memory import ServiceMemorySink

__all__ = [
    "ServiceFileSink",
    "ServiceMemorySink",
]
