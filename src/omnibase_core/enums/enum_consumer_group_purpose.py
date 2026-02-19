# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Consumer Group Purpose Enumeration.

Provides classification values for consumer group purposes in event bus
subscription operations. Used to derive unique consumer group IDs from
node identity combined with purpose.

The purpose value becomes part of the consumer group ID:
    ``{env}.{service}.{node_name}.{purpose}.{version}``

.. versionadded:: 0.14.0
    Added as part of ProtocolEventBusSubscriber refactoring (PR #476).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConsumerGroupPurpose(StrValueHelper, str, Enum):
    """
    Consumer group purpose classification for event bus subscriptions.

    Defines the purpose of a consumer group, which is used to derive
    unique consumer group IDs from node identity. This enables multiple
    consumers from the same node to subscribe to the same topic with
    different processing semantics.

    Attributes:
        CONSUME: Standard message consumption for processing.
        INTROSPECTION: Read-only inspection of messages for debugging or monitoring.
        REPLAY: Replaying historical messages from a topic.
        AUDIT: Audit trail consumption for compliance or logging.
        BACKFILL: Batch processing of historical data.
        CONTRACT_REGISTRY: Contract registry subscription for schema validation.

    Example:
        >>> from omnibase_core.enums import EnumConsumerGroupPurpose
        >>> purpose = EnumConsumerGroupPurpose.CONSUME
        >>> str(purpose)
        'consume'
        >>> purpose == "consume"
        True

    Consumer Group ID Format:
        The purpose becomes part of the consumer group ID derived from node identity:

        >>> # With purpose=CONSUME and node_identity (env=dev, service=my-service,
        >>> # node_name=handler, version=v1):
        >>> # Consumer group ID: "dev.my-service.handler.consume.v1"

    .. versionadded:: 0.14.0
        Added as part of ProtocolEventBusSubscriber node_identity refactoring.
    """

    CONSUME = "consume"
    INTROSPECTION = "introspection"
    REPLAY = "replay"
    AUDIT = "audit"
    BACKFILL = "backfill"
    CONTRACT_REGISTRY = "contract-registry"

    def is_read_only(self) -> bool:
        """
        Check if this purpose represents read-only consumption.

        Read-only purposes do not commit offsets and do not affect
        the processing state of other consumers.

        Returns:
            True if INTROSPECTION or AUDIT, False otherwise.

        Example:
            >>> EnumConsumerGroupPurpose.INTROSPECTION.is_read_only()
            True
            >>> EnumConsumerGroupPurpose.CONSUME.is_read_only()
            False
        """
        return self in {
            EnumConsumerGroupPurpose.INTROSPECTION,
            EnumConsumerGroupPurpose.AUDIT,
        }

    def is_batch_processing(self) -> bool:
        """
        Check if this purpose represents batch processing.

        Batch processing purposes typically process historical data
        rather than real-time streams.

        Returns:
            True if REPLAY or BACKFILL, False otherwise.

        Example:
            >>> EnumConsumerGroupPurpose.BACKFILL.is_batch_processing()
            True
            >>> EnumConsumerGroupPurpose.CONSUME.is_batch_processing()
            False
        """
        return self in {
            EnumConsumerGroupPurpose.REPLAY,
            EnumConsumerGroupPurpose.BACKFILL,
        }


__all__ = ["EnumConsumerGroupPurpose"]
