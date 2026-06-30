# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""
Dispatch Metadata Model.

Provides strongly-typed metadata for dispatch operations, replacing raw dict usage
while maintaining extensibility for custom fields.

Design Pattern:
    ModelDispatchMetadata is a pure data model that captures common dispatch
    metadata fields with strong typing:
    - Source and target node identifiers
    - Retry information
    - Routing decision explanations

    The model uses `extra="allow"` to permit custom metadata fields beyond
    the known typed fields, enabling extensibility for domain-specific needs
    without modifying the core model.

    This model uses sentinel values (empty string) instead of nullable unions
    to minimize union count in the codebase (OMN-1002).

Sentinel Values:
    - Empty string ("") means "not set" for all string fields
    - Use the ``has_*`` properties to check if a field has been set

Thread Safety:
    ModelDispatchMetadata is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelDispatchMetadata
    >>>
    >>> # Create metadata with known fields
    >>> metadata = ModelDispatchMetadata(
    ...     source_node="user-service",
    ...     target_node="notification-service",
    ...     routing_decision="fanout to notification handlers",
    ... )
    >>>
    >>> # Create metadata with custom fields (extra="allow")
    >>> extended = ModelDispatchMetadata(
    ...     source_node="order-service",
    ...     custom_field="custom_value",
    ...     priority="high",
    ... )
    >>> extended.model_extra["custom_field"]
    'custom_value'

See Also:
    omnibase_core.models.dispatch.ModelDispatchResult: Dispatch operation result

.. versionchanged:: 0.7.0
    Refactored to use sentinel values instead of nullable unions (OMN-1004).
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Sentinel value for "not set" state
_SENTINEL_STR: str = ""


class ModelDispatchMetadata(BaseModel):
    """
    Dispatch operation metadata with known fields and extensibility.

    Provides strongly-typed common metadata fields while allowing custom
    metadata via extra="allow" config. This replaces raw dict[str, str]
    usage with a proper Pydantic model that maintains type safety for
    known fields.

    Sentinel Values:
        - Empty string ("") means "not set" for all string fields
        - Use ``has_source_node``, ``has_target_node``, etc. to check

    Null Coercion:
        Constructors accept ``None`` for any field and convert to sentinel.

    Attributes:
        source_node: Identifier of the node that originated the dispatch.
            Empty string if not set.
        target_node: Identifier of the target node receiving the dispatch.
            Empty string if not set.
        retry_reason: Explanation for why this dispatch is a retry attempt.
            Empty string if not set.
        routing_decision: Description of the routing decision that was made.
            Empty string if not set.

    Example:
        >>> # Basic usage with known fields
        >>> meta = ModelDispatchMetadata(
        ...     source_node="event-processor",
        ...     target_node="state-reducer",
        ... )
        >>> meta.has_source_node
        True
        >>>
        >>> # With custom extensibility fields
        >>> meta = ModelDispatchMetadata(
        ...     source_node="api-gateway",
        ...     custom_trace_id="abc123",
        ...     environment="production",
        ... )
        >>> # Access custom fields via model_extra
        >>> meta.model_extra["custom_trace_id"]
        'abc123'

    .. versionchanged:: 0.7.0
        Refactored to use sentinel values instead of nullable unions (OMN-1004).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        from_attributes=True,
    )

    # ---- Known Dispatch Metadata Fields ----
    source_node: str = Field(
        default=_SENTINEL_STR,
        description="Identifier of the node that originated the dispatch. "
        "Empty string if not set.",
    )
    target_node: str = Field(
        default=_SENTINEL_STR,
        description="Identifier of the target node receiving the dispatch. "
        "Empty string if not set.",
    )
    retry_reason: str = Field(
        default=_SENTINEL_STR,
        description="Explanation for why this dispatch is a retry attempt. "
        "Empty string if not set.",
    )
    routing_decision: str = Field(
        default=_SENTINEL_STR,
        description="Description of the routing decision that was made. "
        "Empty string if not set.",
    )

    # ---- Validators for None-to-Sentinel Conversion ----
    @field_validator(
        "source_node", "target_node", "retry_reason", "routing_decision", mode="before"
    )
    @classmethod
    def _convert_none_to_str_sentinel(cls, v: object) -> str:
        """Convert None to empty string sentinel for null coercion."""
        if v is None:
            return _SENTINEL_STR
        if isinstance(v, str):
            return v
        return str(v)

    # ---- Sentinel Check Properties ----
    @property
    def has_source_node(self) -> bool:
        """Check if source_node is set (not empty string)."""
        return self.source_node != _SENTINEL_STR

    @property
    def has_target_node(self) -> bool:
        """Check if target_node is set (not empty string)."""
        return self.target_node != _SENTINEL_STR

    @property
    def has_retry_reason(self) -> bool:
        """Check if retry_reason is set (not empty string)."""
        return self.retry_reason != _SENTINEL_STR

    @property
    def has_routing_decision(self) -> bool:
        """Check if routing_decision is set (not empty string)."""
        return self.routing_decision != _SENTINEL_STR

    @property
    def is_empty(self) -> bool:
        """Check if all known fields are unset (ignoring extra fields)."""
        return (
            not self.has_source_node
            and not self.has_target_node
            and not self.has_retry_reason
            and not self.has_routing_decision
        )

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary with only set fields.

        Returns a dictionary containing only fields that are set (non-empty),
        including any extra fields from model_extra.

        Returns:
            Dictionary with string keys and values.

        Example:
            >>> meta = ModelDispatchMetadata(
            ...     source_node="event-processor",
            ...     custom_field="value",
            ... )
            >>> d = meta.to_dict()
            >>> "source_node" in d
            True
            >>> "target_node" in d  # Empty string excluded
            False
            >>> "custom_field" in d  # Extra fields included
            True

        .. versionadded:: 0.7.0
        """
        result: dict[str, str] = {}
        if self.has_source_node:
            result["source_node"] = self.source_node
        if self.has_target_node:
            result["target_node"] = self.target_node
        if self.has_retry_reason:
            result["retry_reason"] = self.retry_reason
        if self.has_routing_decision:
            result["routing_decision"] = self.routing_decision
        # Include extra fields
        if self.model_extra:
            for key, value in self.model_extra.items():
                if isinstance(value, str):
                    result[key] = value
                else:
                    result[key] = str(value)
        return result


__all__ = ["ModelDispatchMetadata"]
