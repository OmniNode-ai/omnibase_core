"""
TypedDict for envelope routing information.

This TypedDict defines the structure returned by EnvelopeRouter.route_envelope(),
providing typed access to the resolved handler and handler type.

Related:
    - OMN-228: EnvelopeRouter transport-agnostic orchestrator
    - EnvelopeRouter.route_envelope(): Returns this type

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["TypedDictRoutingInfo"]

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_handler_type import EnumHandlerType
    from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler


class TypedDictRoutingInfo(TypedDict):
    """TypedDict for envelope routing information returned by route_envelope.

    Attributes:
        handler: The resolved ProtocolHandler for the envelope's handler_type.
        handler_type: The EnumHandlerType used for routing lookup.
    """

    handler: ProtocolHandler
    handler_type: EnumHandlerType
