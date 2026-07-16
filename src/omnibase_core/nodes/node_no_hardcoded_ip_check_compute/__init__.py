# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_hardcoded_ip_check COMPUTE node package (OMN-14659).

Exposes :class:`NodeNoHardcodedIpCheckCompute` — scans explicit (path,
source) pairs for hardcoded internal IP addresses (RFC1918 ranges
192.168.x.x, 10.x.x.x, 172.16-31.x.x) and returns a
``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.handler import (
    NodeNoHardcodedIpCheckCompute,
)

__all__ = ["NodeNoHardcodedIpCheckCompute"]
