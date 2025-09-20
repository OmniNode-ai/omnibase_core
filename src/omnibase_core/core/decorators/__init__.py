"""Core decorators - direct imports to avoid circular dependencies."""

# Import directly from pattern exclusions to avoid circular import
from omnibase_core.decorators.pattern_exclusions import (
    allow_any_type,
    allow_dict_str_any,
    allow_legacy_pattern,
    allow_mixed_types,
    exclude_from_onex_standards,
)

__all__ = [
    "allow_any_type",
    "allow_dict_str_any",
    "allow_legacy_pattern",
    "allow_mixed_types",
    "exclude_from_onex_standards",
]
