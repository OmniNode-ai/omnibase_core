# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeSprintRollCompute — sprint-roll placement COMPUTE handler.

Regenerates the omni plugin's `sprint-roll` script (OMN-20395) into a canonical COMPUTE
node on the def-B ``handle(request) -> response`` shape. The script form was refused by
the canonical-file-shape gate (OMN-20304) under the operator ruling of 2026-10-01: new
capability is a contract + node + handler, and the shrink-only baseline that grandfathers
90 existing skill scripts cannot grow. The migration precedent is
``node_test_selector_compute``, whose contract records the same move for
``scripts/ci/detect_test_paths.py``.

Architecture: COMPUTE node — pure, deterministic, no I/O. Every fact arrives on
:class:`ModelSprintRollRequest`: the sprint window, the run date, the criterion carrier
lists and their wording. The Linear reads and writes, the write journal and the undo are
the paired EFFECT node's (OMN-20397), never this handler's.

Output is a plan, not an action. Nothing in :class:`ModelSprintRollPlan` has been
written anywhere.

Ticket: OMN-20396 (parent OMN-20395).
"""

from __future__ import annotations

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
    ModelSprintRollPlan,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_request import (
    ModelSprintRollRequest,
)
from omnibase_core.nodes.node_sprint_roll_compute.roll_core import compute_roll

__all__ = ["NodeSprintRollCompute"]


class NodeSprintRollCompute:
    """COMPUTE handler that resolves a sprint roll into a placement plan."""

    def handle(self, request: ModelSprintRollRequest) -> ModelSprintRollPlan:
        """Definition-B canonical entry-point.

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        return compute_roll(request)
