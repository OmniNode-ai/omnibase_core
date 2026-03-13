# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event bus type enumeration for ONEX runtime event bus configuration.

This enum formalizes the allowed event bus types and enforces that
INMEMORY is never used as a production default.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumEventBusType"]


@unique
class EnumEventBusType(StrValueHelper, str, Enum):
    """Supported event bus types for the ONEX runtime.

    Values:
        KAFKA: Kafka/Redpanda-backed event bus. Required for production.
        INMEMORY: In-memory event bus. Test and development use ONLY.
            NEVER use as a production default (raises ValueError on construction
            when env=production).
        CLOUD: Cloud-hosted Kafka bus (e.g. cloud Redpanda via tunnel).

    Notes:
        Setting the event bus type env var to ``inmemory`` is FORBIDDEN for
        runtime sessions. See CLAUDE.md for the full policy on this restriction.
    """

    KAFKA = "kafka"
    INMEMORY = "inmemory"
    CLOUD = "cloud"

    @property
    def is_production_safe(self) -> bool:
        """Return True if this bus type is safe for production use.

        Returns:
            bool: True for KAFKA and CLOUD; False for INMEMORY.

        Example:
            >>> EnumEventBusType.KAFKA.is_production_safe
            True
            >>> EnumEventBusType.INMEMORY.is_production_safe
            False
        """
        return self in {EnumEventBusType.KAFKA, EnumEventBusType.CLOUD}

    @property
    def requires_broker(self) -> bool:
        """Return True if this bus type requires an external broker.

        Returns:
            bool: True for KAFKA and CLOUD; False for INMEMORY.
        """
        return self in {EnumEventBusType.KAFKA, EnumEventBusType.CLOUD}
