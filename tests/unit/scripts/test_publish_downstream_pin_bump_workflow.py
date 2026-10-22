# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard for publish-downstream-pin-bump.yml PR shape (OMN-19848).

Every bot PR the workflow opened for omnibase_core ca5df31c targeted ``main`` in
dev-default repos, so ``main-target-guard`` failed and the PR carried the whole
dev-ahead-of-main history. The title also lacked the ticket token, so the downstream
OCC autobind never minted a companion.
"""

from __future__ import annotations

import json
import os
import subprocess
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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("initial_status", "final_conclusion", "expected_code", "expected_reads"),
    [
        pytest.param("completed", "success", 0, 2, id="null-settles-to-success"),
        pytest.param("completed", None, 1, 6, id="null-exhausts-bound"),
        pytest.param("completed", "failure", 1, 1, id="real-failure"),
        pytest.param("in_progress", "success", 0, 2, id="running-settles-to-success"),
        pytest.param("completed", "skipped", 0, 1, id="skipped-passes"),
    ],
)
def test_publish_summary_settles_leg_conclusions(
    tmp_path: Path,
    initial_status: str,
    final_conclusion: str | None,
    expected_code: int,
    expected_reads: int,
) -> None:
    """OMN-20074: run 39816628531 read null just after successful legs finished."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    (step,) = [
        step
        for step in workflow["jobs"]["summary"]["steps"]
        if step.get("name") == "Fail red on any real leg failure (no silent gates)"
    ]
    script = step["run"].replace(
        "${{ github.repository }}", "OmniNode-ai/omnibase_core"
    )
    script = script.replace("${{ github.run_id }}", "1")
    names = ["Bump: omnibase_infra", "Bump: omnimemory"]
    for snapshot in ("initial", "settled"):
        conclusion = (
            None
            if snapshot == "initial"
            and initial_status == "completed"
            and final_conclusion == "success"
            else final_conclusion
        )
        (tmp_path / f"{snapshot}.json").write_text(
            json.dumps(
                {
                    "jobs": [
                        {
                            "name": name,
                            "status": initial_status
                            if snapshot == "initial"
                            else "completed",
                            "conclusion": conclusion,
                        }
                        for name in names
                    ]
                    + [
                        {
                            "name": "Publish summary",
                            "status": "in_progress",
                            "conclusion": None,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
    counter = tmp_path / "reads"
    counter.write_text("0\n", encoding="utf-8")
    gh = tmp_path / "gh"
    gh.write_text(
        """#!/bin/bash
set -euo pipefail
[[ "$#" -eq 5 && "$1" == "api" && "$3" == "--paginate" && "$4" == "--jq" ]]
[[ "$2" == "repos/OmniNode-ai/omnibase_core/actions/runs/1/jobs" ]]
reads=$(cat "$TEST_ROOT/reads")
echo "$((reads + 1))" > "$TEST_ROOT/reads"
if [ "$reads" -eq 0 ]; then
  snapshot=initial
else
  snapshot=settled
fi
cat "$TEST_ROOT/$snapshot.json" | /usr/bin/jq -r "$5"
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    summary = tmp_path / "summary.md"
    assert step["env"]["SETTLE_ATTEMPTS"] == "6"
    assert step["env"]["SETTLE_SLEEP_SECONDS"] == "10"
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env={
            "PATH": str(tmp_path) + os.pathsep + os.defpath,
            "TEST_ROOT": str(tmp_path),
            "SETTLE_ATTEMPTS": step["env"]["SETTLE_ATTEMPTS"],
            "SETTLE_SLEEP_SECONDS": "0",
            "GITHUB_STEP_SUMMARY": str(summary),
            "GITHUB_TOKEN": "x",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert int(counter.read_text(encoding="utf-8")) == expected_reads
    if expected_code == 1:
        conclusion_text = "null" if final_conclusion is None else final_conclusion
        for name in names:
            assert f"::error::{name}: {conclusion_text}" in result.stdout
            assert f"{name}: {conclusion_text}" in summary.read_text(encoding="utf-8")
