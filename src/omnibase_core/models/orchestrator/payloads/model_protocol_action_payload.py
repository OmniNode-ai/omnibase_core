# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
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
    >>> from omnibase_core.models.orchestrator.payloads import ProtocolActionPayload
    >>> from pydantic import BaseModel, ConfigDict
    >>> from typing import Literal
    >>>
    >>> class ModelPayloadCustomAction(BaseModel):
    ...     model_config = ConfigDict(frozen=True, extra="forbid")
    ...     kind: Literal["custom.action"] = "custom.action"
    ...     data: str
    >>>
    >>> # Conforms to ProtocolActionPayload via structural typing
    >>> payload: ProtocolActionPayload = ModelPayloadCustomAction(data="test")

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
        kind: String identifier for the action type. Used for routing to
            the appropriate handler. Should be a Literal type for type safety.

    Conformance Requirements:
        - Must have a `kind` attribute (read-only string)
        - Should be immutable (frozen=True) for thread safety
        - Should use extra="forbid" for strict schema validation

    Example:
        >>> from pydantic import BaseModel, ConfigDict
        >>> from typing import Literal
        >>>
        >>> class ModelPayloadMyAction(BaseModel):
        ...     model_config = ConfigDict(frozen=True, extra="forbid")
        ...     kind: Literal["my.action"] = "my.action"
        ...     data: str
        >>>
        >>> # Automatically satisfies ProtocolActionPayload
        >>> payload: ProtocolActionPayload = ModelPayloadMyAction(data="test")

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
