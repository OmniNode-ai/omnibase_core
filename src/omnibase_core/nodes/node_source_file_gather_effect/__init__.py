# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""source_file_gather EFFECT node package (OMN-14656).

Exposes :class:`NodeSourceFileGatherEffect` — gathers eligible source files
under a root directory (glob + .onexignore + schema-exclusion + max-size
filtering) and returns them with content inline.
"""

from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

__all__ = ["NodeSourceFileGatherEffect"]
