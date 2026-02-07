"""Interface consumed model for ticket-driven parallel development."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_interface_kind import EnumInterfaceKind
from omnibase_core.enums.ticket.enum_mock_strategy import EnumMockStrategy


class ModelInterfaceConsumed(BaseModel):
    """Interface this ticket consumes (may be mocked during parallel dev).

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the consumed interface")
    name: str = Field(
        ..., description="Interface name (e.g., ProtocolRuntimeEntryPoint)"
    )
    kind: EnumInterfaceKind = Field(..., description="Type of interface")
    source_ticket: str | None = Field(
        default=None, description="Source ticket ID (e.g., OMN-1937)"
    )
    mock_strategy: EnumMockStrategy = Field(
        ..., description="Strategy for mocking this interface"
    )
    required: bool = Field(
        default=True, description="Whether this interface is required"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


# Alias for cleaner imports
InterfaceConsumed = ModelInterfaceConsumed

__all__ = [
    "ModelInterfaceConsumed",
    "InterfaceConsumed",
]
