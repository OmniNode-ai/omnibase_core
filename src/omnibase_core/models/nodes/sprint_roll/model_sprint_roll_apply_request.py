# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Input contract for the sprint-roll APPLY effect node (OMN-20397).

`dry_run` defaults to True. A roll that writes is the exception, not the default,
because the operator's rule is best guess now and audit after the sprint starts -- and an
audit needs the plan the writes were made from, which a dry run is.

`label_sprint_count` carries the rule that every open ticket in the next N sprints
should be beta-critical. It is applied only after the carrier mapping, never before: the
board's reconciliation gate FAILs repo-wide on an open beta-critical ticket that no
carrier list names, so labelling first reddens every open pull request in omninode_infra.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
    ModelSprintRollPlan,
)

__all__ = ["ModelSprintRollApplyRequest"]


class ModelSprintRollApplyRequest(BaseModel):
    """What to apply, and whether to apply it at all."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    plan: ModelSprintRollPlan
    dry_run: bool = True
    manifest_path: Path | None = None
    label_name: str = "beta-critical"
    label_sprint_count: int = 2
