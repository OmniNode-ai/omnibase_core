"""
Protocol for action payloads.

This module defines the ProtocolActionPayload which all action payloads must
implement. Using a Protocol (structural typing) instead of a discriminated union
provides open extensibility for Orchestrator actions.

Design Pattern:
    Protocol-based payloads enable:
    - Open extensibility: Plugins can define their own action payloads
    - Duck typing: Any conforming class works as a payload
    - Decoupling: No central union to modify when adding payloads
    - Structural pattern matching still works via isinstance checks

Architecture:
    Orchestrator emits Actions with Protocol-conforming payloads to direct
    Compute/Reducer nodes on what work to perform.

Thread Safety:
    All conforming payloads should be immutable (frozen=True) after creation.

Example:
    The recommended approach is to inherit from ModelActionPayloadBase, which
    provides the `kind` property automatically derived from `action_type.name`:

    >>> from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
    >>> from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
    >>> from omnibase_core.models.core.model_predefined_categories import OPERATION
    >>> from pydantic import Field
    >>>
    >>> class ModelPayloadCustomAction(ModelActionPayloadBase):
    ...     '''Custom action payload with automatic kind property.'''
    ...     data: str = Field(..., description="Custom data")
    >>>
    >>> # Create with ModelNodeActionType - kind property is auto-derived
    >>> payload = ModelPayloadCustomAction(
    ...     action_type=ModelNodeActionType(
    ...         name="custom.action",
    ...         category=OPERATION,
    ...         display_name="Custom Action",
    ...         description="A custom action",
    ...     ),
    ...     data="test",
    ... )
    >>> payload.kind  # Returns "custom.action" (derived from action_type.name)
    'custom.action'

    Alternatively, implement the kind property directly for standalone payloads:

    >>> from pydantic import BaseModel, ConfigDict
    >>>
    >>> class ModelPayloadStandalone(BaseModel):
    ...     model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    ...     _kind: str = "standalone.action"
    ...     data: str
    ...
    ...     @property
    ...     def kind(self) -> str:
    ...         return self._kind
    >>>
    >>> # Conforms to ProtocolActionPayload via structural typing
    >>> payload: ProtocolActionPayload = ModelPayloadStandalone(data="test")

See Also:
    omnibase_core.models.core.model_action_payload_base: Base class for core action payloads
    omnibase_core.models.orchestrator.model_action: Action model using this protocol
"""

from typing import Protocol, runtime_checkable

# Public API - listed immediately after imports per Python convention
__all__ = [
    "ProtocolActionPayload",
    "ActionPayloadList",
]


@runtime_checkable
class ProtocolActionPayload(Protocol):
    """Protocol for action payloads.

    All action payloads must implement this protocol to be usable with ModelAction.
    The protocol uses structural typing - any class with matching attributes
    satisfies the protocol without explicit inheritance.

    Required Attributes:
        kind: String identifier for the action type (property or attribute).
            Used for routing to the appropriate handler. When inheriting from
            ModelActionPayloadBase, this is automatically provided as a property
            derived from `action_type.name`.

    Conformance Requirements:
        - Must have a `kind` property or attribute (read-only string)
        - Should be immutable (frozen=True) for thread safety
        - Should use extra="forbid" for strict schema validation
        - Should use from_attributes=True for pytest-xdist compatibility

    Example (recommended - inherit from ModelActionPayloadBase):
        >>> from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
        >>> from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
        >>> from omnibase_core.models.core.model_predefined_categories import OPERATION
        >>>
        >>> class ModelPayloadMyAction(ModelActionPayloadBase):
        ...     data: str
        >>>
        >>> # The kind property is auto-derived from action_type.name
        >>> payload = ModelPayloadMyAction(
        ...     action_type=ModelNodeActionType(
        ...         name="my.action", category=OPERATION,
        ...         display_name="My Action", description="Example",
        ...     ),
        ...     data="test",
        ... )
        >>> payload.kind
        'my.action'

    Note:
        The @runtime_checkable decorator enables isinstance() checks:
        >>> isinstance(payload, ProtocolActionPayload)  # True
    """

    @property
    def kind(self) -> str:
        """Action type identifier for routing.

        Used to dispatch to the appropriate handler in Compute/Reducer nodes.
        Should return a dot-separated namespace (e.g., "data.transform", "lifecycle.start").

        Returns:
            str: The action type identifier.
        """
        ...


# Type alias for list of action payloads
ActionPayloadList = list[ProtocolActionPayload]
"""Type alias for lists of action payloads."""
