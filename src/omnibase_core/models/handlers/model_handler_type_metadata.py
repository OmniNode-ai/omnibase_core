# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Type Metadata Model.

Describes replay behavior, security requirements, and execution semantics for handler types.
Follows ONEX one-model-per-file architecture.

This module provides:
    - :class:`ModelHandlerTypeMetadata`: Pydantic model describing handler type behavior
    - :func:`get_handler_type_metadata`: Factory function to get metadata for a category

The metadata is used for:
    - **Caching decisions**: COMPUTE handlers can be safely cached; EFFECT handlers cannot
    - **Retry policies**: EFFECT handlers may need idempotency checks; COMPUTE handlers can retry freely
    - **Replay safety**: Determining which handlers can be safely replayed during recovery
    - **Secret management**: Determining which handlers need access to secrets

Decision Matrix (from EnumHandlerTypeCategory):
    +---------------------------+---------------+-------------------+--------------+
    | Category                  | Pure (no I/O) | Deterministic     | Replay Safe  |
    +===========================+===============+===================+==============+
    | COMPUTE                   | Yes           | Yes               | Yes          |
    +---------------------------+---------------+-------------------+--------------+
    | NONDETERMINISTIC_COMPUTE  | Yes           | No                | No           |
    +---------------------------+---------------+-------------------+--------------+
    | EFFECT                    | No            | N/A (has I/O)     | No           |
    +---------------------------+---------------+-------------------+--------------+

Example:
    >>> from omnibase_core.models.handlers import get_handler_type_metadata
    >>> from omnibase_core.enums import EnumHandlerTypeCategory
    >>>
    >>> # Get metadata for COMPUTE category
    >>> meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
    >>> meta.is_replay_safe
    True
    >>> meta.requires_secrets
    False
    >>>
    >>> # Get metadata for EFFECT category
    >>> effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
    >>> effect_meta.is_replay_safe
    False
    >>> effect_meta.requires_secrets
    True

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Behavioral classification of handlers
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      External system classification (HTTP, DATABASE, etc.)

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1121 handler type metadata.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory


class ModelHandlerTypeMetadata(BaseModel):
    """Metadata describing handler type behavior.

    This model provides a structured way to query the behavioral characteristics
    of a handler based on its category. The metadata is pre-defined for each
    handler type category and can be retrieved via :func:`get_handler_type_metadata`.

    Attributes:
        category: The handler type category (COMPUTE, EFFECT, NONDETERMINISTIC_COMPUTE)
        is_replay_safe: Whether handler can be safely replayed during recovery.
            True for deterministic handlers (same input = same output).
        requires_secrets: Whether handler needs access to secrets/credentials.
            True for EFFECT handlers that interact with external systems.
        is_deterministic: Whether handler produces deterministic output.
            True only for COMPUTE handlers; False for EFFECT and NONDETERMINISTIC_COMPUTE.
        allows_caching: Whether handler results can be cached.
            True for COMPUTE and NONDETERMINISTIC_COMPUTE (with appropriate keys).
        requires_idempotency_key: Whether handler needs idempotency key for replay.
            True for non-deterministic handlers to track execution state.

    Example:
        >>> from omnibase_core.enums import EnumHandlerTypeCategory
        >>> metadata = ModelHandlerTypeMetadata(
        ...     category=EnumHandlerTypeCategory.COMPUTE,
        ...     is_replay_safe=True,
        ...     requires_secrets=False,
        ...     is_deterministic=True,
        ...     allows_caching=True,
        ...     requires_idempotency_key=False,
        ... )
        >>> metadata.is_replay_safe
        True

    Note:
        Use :func:`get_handler_type_metadata` to get pre-defined metadata
        for a category rather than constructing instances manually.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    category: EnumHandlerTypeCategory
    is_replay_safe: bool
    requires_secrets: bool
    is_deterministic: bool
    allows_caching: bool
    requires_idempotency_key: bool

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelHandlerTypeMetadata("
            f"category={self.category.value}, "
            f"replay_safe={self.is_replay_safe}, "
            f"deterministic={self.is_deterministic})"
        )


# Pre-defined metadata for each category
_HANDLER_TYPE_METADATA: dict[EnumHandlerTypeCategory, ModelHandlerTypeMetadata] = {
    EnumHandlerTypeCategory.COMPUTE: ModelHandlerTypeMetadata(
        category=EnumHandlerTypeCategory.COMPUTE,
        is_replay_safe=True,
        requires_secrets=False,
        is_deterministic=True,
        allows_caching=True,
        requires_idempotency_key=False,
    ),
    EnumHandlerTypeCategory.EFFECT: ModelHandlerTypeMetadata(
        category=EnumHandlerTypeCategory.EFFECT,
        is_replay_safe=False,
        requires_secrets=True,
        is_deterministic=False,
        allows_caching=False,
        requires_idempotency_key=True,
    ),
    EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE: ModelHandlerTypeMetadata(
        category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
        is_replay_safe=False,
        requires_secrets=False,
        is_deterministic=False,
        allows_caching=True,
        requires_idempotency_key=True,
    ),
}


def get_handler_type_metadata(
    category: EnumHandlerTypeCategory,
) -> ModelHandlerTypeMetadata:
    """Get metadata for a handler type category.

    This factory function returns pre-defined metadata describing the behavioral
    characteristics of a handler category. Use this instead of constructing
    :class:`ModelHandlerTypeMetadata` instances manually.

    Args:
        category: The handler type category to get metadata for

    Returns:
        Metadata describing the handler type's behavior

    Raises:
        KeyError: If the category is not recognized (should not happen with
            valid EnumHandlerTypeCategory values)

    Example:
        >>> from omnibase_core.enums import EnumHandlerTypeCategory
        >>> meta = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
        >>> meta.is_replay_safe
        True
        >>> meta.requires_secrets
        False
        >>>
        >>> # EFFECT handlers have different characteristics
        >>> effect_meta = get_handler_type_metadata(EnumHandlerTypeCategory.EFFECT)
        >>> effect_meta.is_replay_safe
        False
        >>> effect_meta.requires_secrets
        True

    Note:
        The returned metadata instances are pre-defined and immutable.
        Multiple calls with the same category return the same instance.
    """
    return _HANDLER_TYPE_METADATA[category]


__all__ = [
    "ModelHandlerTypeMetadata",
    "get_handler_type_metadata",
]
