# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""sprint_roll apply EFFECT node package (OMN-20397).

Exposes :class:`NodeSprintRollApplyEffect` — the only half of the sprint roll that
writes. Its placement decisions come from the paired COMPUTE node (OMN-20396).
"""

from omnibase_core.nodes.node_sprint_roll_apply_effect.handler import (
    NodeSprintRollApplyEffect,
)

__all__ = ["NodeSprintRollApplyEffect"]
