# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Interface Surface Enum.

Categories of interface surfaces that can be touched by changes.
"""

from enum import Enum, unique


@unique
class EnumInterfaceSurface(str, Enum):
    """Categories of interface surfaces in ONEX architecture.

    Interface surfaces define what types of boundaries can be affected:
    - events: Event schemas/models
    - topics: Topic map, routing keys, partition keys
    - protocols: SPI protocol interfaces, public runtime interfaces
    - envelopes: Envelope models, headers
    - public_api: Exported/consumed APIs
    """

    EVENTS = "events"
    """Event schemas/models."""

    TOPICS = "topics"
    """Topic map, routing keys, partition keys."""

    PROTOCOLS = "protocols"
    """SPI protocol interfaces, public runtime interfaces."""

    ENVELOPES = "envelopes"
    """Envelope models, headers."""

    PUBLIC_API = "public_api"
    """Exported/consumed APIs."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
