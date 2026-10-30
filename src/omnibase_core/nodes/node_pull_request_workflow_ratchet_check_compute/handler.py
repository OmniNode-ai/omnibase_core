# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the pull-request workflow ratchet (OMN-14907)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_check_input import (
    ModelPullRequestWorkflowRatchetCheckInput,
)
from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_check_output import (
    ModelPullRequestWorkflowRatchetCheckOutput,
)
from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_gap_entry import (
    ModelPullRequestWorkflowRatchetGapEntry,
)
from omnibase_core.validation.validator_pull_request_workflow_ratchet import (
    verify_pull_request_workflow_ratchet,
)


class NodePullRequestWorkflowRatchetCheckCompute:
    """Return the count-locked-ratchet gaps for one repository."""

    def handle(
        self, request: ModelPullRequestWorkflowRatchetCheckInput
    ) -> ModelPullRequestWorkflowRatchetCheckOutput:
        gaps = verify_pull_request_workflow_ratchet(
            repo_root=Path(request.repo_root),
            registry_path=Path(request.registry_path),
            horizon_days=request.horizon_days,
        )
        return ModelPullRequestWorkflowRatchetCheckOutput(
            gaps=[
                ModelPullRequestWorkflowRatchetGapEntry(
                    workflow_file=g.workflow_file, code=g.code, detail=g.detail
                )
                for g in gaps
            ]
        )
