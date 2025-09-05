"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
"""

from typing import Any, Dict, Union

# Scalar types for message data and metadata
ScalarValue = Union[str, int, float, bool]

# Placeholder for ModelStateValue - adjust based on actual requirements
ModelStateValue = Union[str, int, float, bool, Dict[str, Any], None]
