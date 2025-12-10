"""
Type aliases for effect operation results.

This module provides centralized type aliases for effect operation result types,
eliminating the need for scattered inline unions throughout the codebase.

These type aliases follow ONEX patterns by:
1. Reducing inline union type duplication (anti-pattern: "primitive soup")
2. Providing semantic naming for common return types
3. Centralizing type definitions for easier maintenance

Usage:
    >>> from omnibase_core.types.type_effect_result import (
    ...     EffectResultType,
    ...     DbParamType,
    ... )
    >>>
    >>> # Use in function signatures
    >>> async def execute_effect(...) -> EffectResultType:
    ...     pass
    >>>
    >>> # Use in variable annotations
    >>> result: EffectResultType = {}

See Also:
    - omnibase_core.models.effect.model_effect_output: Uses EffectResultType
    - omnibase_core.mixins.mixin_effect_execution: Uses both type aliases
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Effect architecture
"""

from typing import Any

__all__ = [
    "EffectResultType",
    "DbParamType",
]

# Type alias for effect operation results.
# Used by NodeEffect operations that can return:
# - Primitives: str, int, float, bool (simple values)
# - Complex: dict[str, Any], list[Any] (JSON-like structures)
#
# NOTE: This does NOT include None - effect results are always defined.
# Use Optional[EffectResultType] if None is a valid result.
#
# Replaces inline unions like:
#   str | int | float | bool | dict[str, Any] | list[Any]
EffectResultType = str | int | float | bool | dict[str, Any] | list[Any]

# Type alias for database query parameters.
# Used by DB effect handlers for parameterized queries where:
# - Primitives: str, int, float, bool (direct SQL values)
# - None: NULL value in SQL
#
# Replaces inline unions like:
#   str | int | float | bool | None
DbParamType = str | int | float | bool | None
