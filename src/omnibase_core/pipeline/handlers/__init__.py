"""
Handler capabilities for ONEX pipeline.

This module contains handler implementations that replace mixin-based patterns
with composition-based handlers for the ONEX pipeline.

.. versionadded:: 0.4.0
    Added as part of Mixin-to-Handler conversion (OMN-1112)
"""

from omnibase_core.pipeline.handlers.handler_capability_caching import (
    HandlerCapabilityCaching,
)
from omnibase_core.pipeline.handlers.handler_capability_metrics import (
    HandlerCapabilityMetrics,
)

__all__ = [
    "HandlerCapabilityCaching",
    "HandlerCapabilityMetrics",
]
