"""
ONEX Pattern Exclusion Decorators.
Provides decorators to mark legitimate exceptions to ONEX zero tolerance standards.
"""

from .error_handling import (
    io_error_handling,
    standard_error_handling,
    validation_error_handling,
)
from .pattern_exclusions import (
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
    "io_error_handling",
    "standard_error_handling",
    "validation_error_handling",
]
