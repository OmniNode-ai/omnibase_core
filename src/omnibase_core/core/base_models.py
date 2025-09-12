"""
Base models for ONEX Core Framework.

Standard model aliases for core framework components.
"""

# Core model aliases
from omnibase_core.models.core.model_onex_internal_input_state import (
    ModelOnexInternalInputState as OnexInputState,
)
from omnibase_core.models.core.model_onex_output_state import (
    ModelOnexOutputState as OnexOutputState,
)

__all__ = [
    "OnexInputState",
    "OnexOutputState",
]
