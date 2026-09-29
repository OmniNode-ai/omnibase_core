# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard for publish-downstream-pin-bump.yml PR shape (OMN-19848).

Every bot PR the workflow opened for omnibase_core ca5df31c targeted ``main`` in
dev-default repos, so ``main-target-guard`` failed and the PR carried the whole
dev-ahead-of-main history. The title also lacked the ticket token, so the downstream
OCC autobind never minted a companion.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "publish-downstream-pin-bump.yml"
)


@pytest.fixture(scope="module")
def open_pr_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["bump"]["steps"]
    (step,) = [s for s in steps if s.get("name") == "Open PR + enable auto-merge"]
    return str(step["run"])


@pytest.mark.unit
def test_base_is_the_downstream_default_branch(open_pr_script: str) -> None:
    assert "--base main" not in open_pr_script
    assert ".default_branch" in open_pr_script
    assert '--base "$BASE"' in open_pr_script


@pytest.mark.unit
def test_existing_pr_is_retargeted_to_the_resolved_base(open_pr_script: str) -> None:
    edit_lines = [ln for ln in open_pr_script.splitlines() if "gh pr edit" in ln]
    assert edit_lines
    assert all('--base "$BASE"' in ln for ln in edit_lines)


@pytest.mark.unit
def test_title_carries_the_ticket_token(open_pr_script: str) -> None:
    (title_line,) = [
        ln for ln in open_pr_script.splitlines() if ln.strip().startswith("TITLE=")
    ]
    assert "[OMN-9050]" in title_line
