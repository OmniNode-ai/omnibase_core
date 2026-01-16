"""
Protocol Handler Type Resolver.

Defines the protocol for resolving handler types from various inputs.
Follows ONEX one-model-per-file architecture.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1121 handler type metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
    from omnibase_core.models.handlers.model_handler_type_metadata import (
        ModelHandlerTypeMetadata,
    )


@runtime_checkable
class ProtocolHandlerTypeResolver(Protocol):
    """Protocol for resolving handler types from various inputs.

    This protocol defines the interface for components that can determine
    the handler type category from a handler instance or other input,
    and retrieve the corresponding metadata.

    Implementers can use various strategies to resolve handler types:
        - Inspection of handler attributes or methods
        - Decorator metadata
        - Registration lookups
        - Type analysis

    Example:
        >>> class MyResolver:
        ...     def resolve(self, handler: Any) -> EnumHandlerTypeCategory:
        ...         if hasattr(handler, 'is_effect') and handler.is_effect:
        ...             return EnumHandlerTypeCategory.EFFECT
        ...         return EnumHandlerTypeCategory.COMPUTE
        ...
        ...     def get_metadata(
        ...         self, category: EnumHandlerTypeCategory
        ...     ) -> ModelHandlerTypeMetadata:
        ...         return get_handler_type_metadata(category)
    """

    def resolve(self, handler: Any) -> EnumHandlerTypeCategory:
        """Resolve the handler type category for a given handler.

        Args:
            handler: The handler to resolve. Can be a callable, class instance,
                or any object that can be analyzed to determine its category.

        Returns:
            The handler type category
        """
        ...

    def get_metadata(
        self, category: EnumHandlerTypeCategory
    ) -> ModelHandlerTypeMetadata:
        """Get metadata for a handler type category.

        Args:
            category: The handler type category

        Returns:
            Metadata describing the handler type's behavior
        """
        ...


__all__ = [
    "ProtocolHandlerTypeResolver",
]
