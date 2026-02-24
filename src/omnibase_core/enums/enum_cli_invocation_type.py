# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Invocation Type Enum.

Defines how a CLI command is dispatched when invoked via the
registry-driven CLI system.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliInvocationType(StrValueHelper, str, Enum):
    """
    Invocation types for CLI commands registered via cli.contribution.v1.

    Determines the dispatch mechanism used when the CLI runtime executes
    a registered command.

    Values:
        KAFKA_EVENT: Dispatched as a Kafka event to a topic.
        DIRECT_CALL: Invoked directly via Python callable (local node).
        HTTP_ENDPOINT: Forwarded as an HTTP request to a service endpoint.
        SUBPROCESS: Executed as an OS subprocess.
    """

    KAFKA_EVENT = "kafka_event"
    DIRECT_CALL = "direct_call"
    HTTP_ENDPOINT = "http_endpoint"
    SUBPROCESS = "subprocess"

    @classmethod
    def is_async(cls, invocation_type: "EnumCliInvocationType") -> bool:
        """Return True if the invocation type is inherently asynchronous."""
        return invocation_type == cls.KAFKA_EVENT

    @classmethod
    def is_network_bound(cls, invocation_type: "EnumCliInvocationType") -> bool:
        """Return True if the invocation type requires network access."""
        return invocation_type in {cls.KAFKA_EVENT, cls.HTTP_ENDPOINT}


__all__ = ["EnumCliInvocationType"]
