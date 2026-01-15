"""
ONEX Pattern Exclusion Decorators.
Provides decorators to mark legitimate exceptions to ONEX strict typing standards.
"""

from .decorator_allow_dict_any import allow_dict_any
from .decorator_convert_to_schema import (
    convert_dict_to_schema,
    convert_list_to_schema,
    convert_to_schema,
)
from .decorator_effect_boundary import (
    EFFECT_BOUNDARY_ATTR,
    effect_boundary,
    get_effect_boundary,
    has_effect_boundary,
)
from .decorator_enforce_execution_shape import enforce_execution_shape
from .decorator_error_handling import (
    io_error_handling,
    standard_error_handling,
    validation_error_handling,
)
from .decorator_pattern_exclusions import (
    allow_any_type,
    allow_legacy_pattern,
    allow_mixed_types,
    exclude_from_onex_standards,
)

__all__ = [
    "EFFECT_BOUNDARY_ATTR",
    "allow_any_type",
    "allow_dict_any",
    "allow_legacy_pattern",
    "allow_mixed_types",
    "convert_dict_to_schema",
    "convert_list_to_schema",
    "convert_to_schema",
    "effect_boundary",
    "enforce_execution_shape",
    "exclude_from_onex_standards",
    "get_effect_boundary",
    "has_effect_boundary",
    "io_error_handling",
    "standard_error_handling",
    "validation_error_handling",
]
