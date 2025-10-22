import json
from typing import Generic, TypeVar, Union

__all__ = [
    "BoolContainer",
    "DictContainer",
    "FloatContainer",
    "IntContainer",
    "ListContainer",
    "ModelTypedMapping",
    "ModelValueContainer",
    "StringContainer",
    "ValidatableValue",
]

"""
Generic Value Container Models

Proper generic implementation to replace loose Union types throughout the codebase.
Uses generic containers with protocol constraints instead of discriminated unions,
following ONEX architecture patterns for type safety.

This replaces patterns like Union[str, int, float, bool, dict[str, Any], list[Any]] with
type-safe generic containers that preserve exact type information.
"""

from typing import Any

# Import protocols from omnibase_spi (centralized location)
from omnibase_spi.protocols.types import (
    ProtocolModelJsonSerializable as ModelProtocolJsonSerializable,
)
from omnibase_spi.protocols.types import (
    ProtocolModelValidatable as ModelProtocolValidatable,
)

# Import extracted classes
from .model_typed_mapping import ModelTypedMapping
from .model_value_container import ModelValueContainer

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
