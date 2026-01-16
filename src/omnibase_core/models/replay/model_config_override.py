"""
Single configuration override specification for replay injection.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.replay.enum_override_injection_point import (
    EnumOverrideInjectionPoint,
)

__all__ = ["ModelConfigOverride"]


class ModelConfigOverride(BaseModel):
    """
    A single configuration override specification.

    Attributes:
        path: Dot-separated path to the config field (e.g., "llm.openai.temperature").
        value: The new value to set at this path.
        injection_point: Where to apply this override (handler_config, environment, context).

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for concurrent reads.

    Example:
        >>> override = ModelConfigOverride(
        ...     path="llm.temperature",
        ...     value=0.7,
        ...     injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        ... )
    """

    # from_attributes=True: Enables construction from ORM/dataclass instances
    # and ensures pytest-xdist compatibility across worker processes where
    # class identity may differ due to independent imports.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(
        ...,
        min_length=1,
        description="Dot-separated path to the config field",
    )
    value: Any = Field(
        ...,
        description="The new value to set at this path",
    )
    injection_point: EnumOverrideInjectionPoint = Field(
        default=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        description="Where to apply this override",
    )
