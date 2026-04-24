# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enum for agent-level protocol classification.

Meaningful only when EnumInvocationKind == AGENT. Classifies the wire protocol
used to communicate with the remote agent peer (e.g., A2A). This is a higher-
level concept layered on transport — do NOT conflate with EnumInfraTransportType,
which tags infrastructure-level transport failures.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAgentProtocol(StrValueHelper, str, Enum):
    """Agent-level protocol used to invoke a remote agent.

    Applicable only when the invocation kind is AGENT. Each value names a
    distinct agent-interoperability protocol with its own lifecycle semantics.
    """

    A2A = "A2A"


__all__ = ["EnumAgentProtocol"]
