# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumContractInterfaceSurface — interface surface values for ticket contract governance.

OMN-10064 / OMN-9582: Added to core as the canonical enum for
ModelTicketContract.interfaces_touched. Values match the OCC-local
EnumInterfaceSurface so on-disk YAML contracts continue to validate.

NOTE: This enum is DISTINCT from EnumInterfaceSurface in
omnibase_core/enums/ticket/enum_interface_surface.py, which serves
a different purpose (node interface kind taxonomy). Do not merge them.
OCC re-exports this enum as its EnumInterfaceSurface alias after Task 4.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumContractInterfaceSurface(str, Enum):
    """Interface surfaces tracked in ticket contracts.

    Values correspond directly to OCC-local EnumInterfaceSurface values
    used in 46+ on-disk contract YAMLs.
    """

    EVENTS = "events"
    """Kafka event schemas published or consumed by this ticket."""

    TOPICS = "topics"
    """Kafka topic declarations touched by this ticket."""

    PROTOCOLS = "protocols"
    """SPI/protocol definitions (ProtocolEventBus, etc.) changed."""

    ENVELOPES = "envelopes"
    """Event envelope schemas modified."""

    PUBLIC_API = "public_api"
    """Public REST/gRPC/WebSocket API surface changes."""

    def __str__(self) -> str:
        """Return the string value for YAML serialization."""
        return self.value


__all__ = ["EnumContractInterfaceSurface"]
