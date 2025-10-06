import json
from typing import Dict, Generic, List, TypeVar, Union

"""
Generic Value Container Models

Proper generic implementation to replace loose Union types throughout the codebase.
Uses generic containers with protocol constraints instead of discriminated unions,
following ONEX architecture patterns for type safety.

This replaces patterns like Union[str, int, float, bool, dict[str, Any], list[Any]] with
type-safe generic containers that preserve exact type information.
"""

from typing import Any, TypeVar

# Import extracted classes
from .model_typed_mapping import ModelTypedMapping
from .model_value_container import ModelValueContainer
from .protocol_model_json_serializable import ModelProtocolJsonSerializable
from .protocol_model_validatable import ModelProtocolValidatable

# Type alias for JSON-serializable values
SerializableValue = str | int | float | bool | list[Any] | dict[str, Any] | None

ValidatableValue = TypeVar("ValidatableValue", bound=ModelProtocolValidatable)

# Type aliases for common patterns
StringContainer = ModelValueContainer
IntContainer = ModelValueContainer
FloatContainer = ModelValueContainer
BoolContainer = ModelValueContainer
ListContainer = ModelValueContainer
DictContainer = ModelValueContainer


# ARCHITECTURAL PRINCIPLE: Strong Typing Only
#
# ❌ NO string paths - always use Path objects
# ❌ NO string versions - always use ModelSemVer objects
# ❌ NO Union[Path, str] fallbacks - choose one type and stick to it
# ❌ NO "convenience" conversion methods - use proper types from the start
#
# ✅ file_path: Path (not str | Path)
# ✅ version: ModelSemVer (not str | ModelSemVer)
# ✅ timestamp: datetime (not str | datetime)
#
# This prevents type confusion, platform issues, and API inconsistencies.
