"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
"""

from omnibase_core.model.core.model_scalar_value import ModelScalarValue
from omnibase_core.model.core.model_state_value import (
    ModelStateValue as ModelStateValueType,
)

# Scalar types for message data and metadata - now using Pydantic model
ScalarValue = ModelScalarValue

# State value type - now using Pydantic model
ModelStateValue = ModelStateValueType
