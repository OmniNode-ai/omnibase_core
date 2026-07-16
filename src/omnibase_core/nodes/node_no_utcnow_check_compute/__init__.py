# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_utcnow_check COMPUTE node package (OMN-14656).

Exposes :class:`NodeNoUtcnowCheckCompute` — AST-scans explicit (path, source)
pairs for ``datetime.utcnow()`` usage and returns an OMN-2362
``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_utcnow_check_compute.handler import (
    NodeNoUtcnowCheckCompute,
)

__all__ = ["NodeNoUtcnowCheckCompute"]
