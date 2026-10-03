# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""sprint_roll COMPUTE node package (OMN-20396).

Exposes :class:`NodeSprintRollCompute` — the canonical form of the omni plugin's
sprint-roll placement arithmetic (OMN-20395). Pure, deterministic, def-B
``handle(request) -> response``; emits :class:`ModelSprintRollPlan`.
"""

from omnibase_core.nodes.node_sprint_roll_compute.handler import NodeSprintRollCompute

__all__ = ["NodeSprintRollCompute"]
