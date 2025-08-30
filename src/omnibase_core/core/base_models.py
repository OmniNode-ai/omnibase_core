"""
Base models for ONEX Core Framework.

This module provides legacy aliases for backward compatibility
with existing tool implementations.
"""

# Legacy aliases for backward compatibility
from omnibase_core.model.core.model_onex_internal_input_state import \
    ModelOnexInternalInputState as OnexInputState
from omnibase_core.model.core.model_onex_output_state import \
    ModelOnexOutputState as OnexOutputState

__all__ = [
    "OnexInputState",
    "OnexOutputState",
]
