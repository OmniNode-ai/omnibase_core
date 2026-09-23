# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18334/OMN-16359: CI retains the companion-effect trigger surface.

The migrated reusable caller lives in ci.yml so it remains visible to CI
Summary. The five activity types and unrestricted PR bases retain the original
description-edit, draft-to-ready, reopen, and stacked-PR coverage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

pytestmark = pytest.mark.unit

EXPECTED_TYPES = {
    "opened",
    "edited",
    "synchronize",
    "reopened",
    "ready_for_review",
}


def _pull_request_trigger() -> dict[str, Any]:
    """Return CI's parsed pull-request trigger block."""
    doc: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))
    assert isinstance(triggers, dict), f"unreadable trigger block: {triggers!r}"
    pull_request = triggers.get("pull_request")
    assert isinstance(pull_request, dict), (
        f"ci.yml has no pull_request mapping: {pull_request!r}"
    )
    return pull_request


def test_ci_retains_the_companion_effect_activity_types() -> None:
    trigger = _pull_request_trigger()
    types = trigger.get("types")
    assert isinstance(types, list), f"CI has no pull_request types: {types!r}"
    assert {str(activity) for activity in types} == EXPECTED_TYPES


def test_ci_has_no_base_branch_filter() -> None:
    """Feature-base PRs must still mint their companion after later retargeting."""
    assert "branches" not in _pull_request_trigger()


def test_ci_job_preserves_required_reusable_contract() -> None:
    doc: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["occ-companion-effect"]
    assert isinstance(job, dict)
    assert job.get("uses") == (
        "OmniNode-ai/omniclaude/.github/workflows/"
        "call-occ-companion-effect-reusable.yml@dev"
    )
    assert job.get("secrets") == "inherit"
    assert job.get("with") == {"lane": "dev"}
    assert "if" not in job
    assert job.get("concurrency") == {
        "group": (
            "OCC Companion Effect Publisher-"
            "${{ github.event.pull_request.number || github.ref }}"
        ),
        "cancel-in-progress": True,
    }
