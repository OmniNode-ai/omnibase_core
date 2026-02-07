"""Interface provided model for ticket-driven parallel development."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_definition_format import EnumDefinitionFormat
from omnibase_core.enums.ticket.enum_interface_kind import EnumInterfaceKind
from omnibase_core.enums.ticket.enum_interface_surface import EnumInterfaceSurface


class ModelInterfaceProvided(BaseModel):
    """Interface this ticket provides to other tickets.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the interface")
    name: str = Field(
        ..., description="Interface name (e.g., ProtocolRuntimeEntryPoint)"
    )
    kind: EnumInterfaceKind = Field(..., description="Type of interface")
    surface: EnumInterfaceSurface = Field(
        ..., description="Where the interface is exposed"
    )
    definition_format: EnumDefinitionFormat = Field(
        ..., description="Format of the definition"
    )
    definition: str = Field(..., description="The actual interface definition")
    definition_hash: str | None = Field(
        default=None, description="SHA256 of normalized definition"
    )
    definition_location: Literal["inline", "file_ref"] = Field(
        default="inline", description="Where the definition is stored"
    )
    definition_ref: str | None = Field(
        default=None,
        description="File path:symbol when definition_location='file_ref'",
    )
    intended_module_path: str | None = Field(
        default=None, description="Where the interface WILL live"
    )
    version: str | None = Field(default=None, description="SemVer if applicable")

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


# Alias for cleaner imports
InterfaceProvided = ModelInterfaceProvided

__all__ = [
    "ModelInterfaceProvided",
    "InterfaceProvided",
]
