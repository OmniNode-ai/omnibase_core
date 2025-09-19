"""Core decorators - alias to main decorators package."""

# Re-export from main decorators package
from ...decorators import (
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
