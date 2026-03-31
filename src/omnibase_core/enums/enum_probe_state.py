# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumProbeState: Authority level returned by a backend probe."""

from enum import Enum, unique


@unique
class EnumProbeState(str, Enum):
    """Authority level returned by a backend probe.

    States:
        DISCOVERED: entry point found, class loaded successfully
        REACHABLE: network endpoint responds (TCP connect)
        HEALTHY: endpoint passes protocol-specific health check
        AUTHORITATIVE: healthy AND explicitly configured or highest-priority
    """

    DISCOVERED = "discovered"
    REACHABLE = "reachable"
    HEALTHY = "healthy"
    AUTHORITATIVE = "authoritative"
