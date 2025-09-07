"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
Now uses strongly typed Pydantic models instead of loose Union types.
"""

from typing import Any, Dict, Union

from omnibase_core.model.core.model_scalar_value import (
    ModelScalarValue,
    ModelScalarValueWrapper,
)
from omnibase_core.model.core.model_state_value import (
    ModelStateValue as TypedModelStateValue,
    ModelStateValueWrapper,
)

# Legacy type aliases for backward compatibility
# These should be gradually replaced with the typed models above
ScalarValue = Union[str, int, float, bool]
ModelStateValue = Union[str, int, float, bool, Dict[str, Any], None]

# New strongly typed versions
# Use these for new code and when refactoring
TypedScalarValue = ModelScalarValue
TypedStateValue = TypedModelStateValue

__all__ = [
    "ScalarValue",  # Deprecated - use TypedScalarValue
    "ModelStateValue",  # Deprecated - use TypedStateValue
    "TypedScalarValue",
    "TypedStateValue",
    "ModelScalarValueWrapper",
    "ModelStateValueWrapper",
]
