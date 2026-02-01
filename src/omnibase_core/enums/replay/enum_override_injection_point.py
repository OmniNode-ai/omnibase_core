"""EnumOverrideInjectionPoint - Injection points for config overrides.

Defines where configuration overrides can be applied during replay execution.
This is a CLOSED vocabulary - new injection points require explicit addition.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOverrideInjectionPoint(StrValueHelper, str, Enum):
    """Injection points for configuration overrides during replay.

    Defines WHERE configuration overrides can be applied during replay
    execution. This is a closed vocabulary - new injection points require
    explicit addition.

    - **HANDLER_CONFIG**: Patch handler configuration model (pre-execution).
      Applied before handler execution begins.

    - **ENVIRONMENT**: Environment variable overlay (NOT os.environ mutation).
      Provides isolated environment context without affecting global state.

    - **CONTEXT**: Patch replay context fields (copy only, not original).
      Modifies a copy of the context to avoid side effects.

    Thread Safety:
        Enum values are immutable and thread-safe.

    Example:
        >>> point = EnumOverrideInjectionPoint.HANDLER_CONFIG
        >>> point == "handler_config"
        True
        >>> EnumOverrideInjectionPoint("environment")
        <EnumOverrideInjectionPoint.ENVIRONMENT: 'environment'>

    .. versionadded:: 0.4.0
    """

    HANDLER_CONFIG = "handler_config"
    """Patch handler configuration model (pre-execution)."""

    ENVIRONMENT = "environment"
    """Environment variable overlay (NOT os.environ mutation)."""

    CONTEXT = "context"
    """Patch replay context fields (copy only, not original)."""


__all__ = ["EnumOverrideInjectionPoint"]
