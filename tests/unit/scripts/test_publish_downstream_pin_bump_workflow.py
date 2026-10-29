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
    # Both modes share this PR step; metadata is prepared once in GITHUB_ENV.
    assert '--title "$TITLE"' in open_pr_script
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["bump"]["steps"]
    metadata = next(s["run"] for s in steps if s.get("name") == "Prepare PR metadata")
    assert "[OMN-9050]" in metadata
    assert "[OMN-21478]" in metadata


@pytest.mark.unit
def test_workflow_triggers_and_matrix_object_shape() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML's YAML 1.1 resolver reads the Actions `on` key as True.
    assert workflow[True]["push"]["branches"] == ["main", "dev"]
    assert "override_tag" in workflow[True]["workflow_dispatch"]["inputs"]
    bump = workflow["jobs"]["bump"]
    assert bump["name"] == "Bump: ${{ matrix.repo }}"
    assert bump["strategy"]["matrix"] == {
        "include": "${{ fromJson(needs.enumerate-repos.outputs.repos) }}"
    }
    assert bump["env"]["REPO"] == "${{ matrix.repo }}"
    assert bump["env"]["MODE"] == "${{ matrix.mode }}"
    steps = {s.get("name"): s for s in bump["steps"]}
    assert (
        steps["Install uv"]["uses"]
        == "astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884"
    )
    for name in (
        "Install uv",
        "Install omnibase_core handler",
        "Update dependency lock",
    ):
        assert steps[name]["if"] == "matrix.mode == 'dependency'"
    step_names = [step.get("name") for step in bump["steps"]]
    assert (
        step_names.index("Install uv")
        < step_names.index("Install omnibase_core handler")
        < step_names.index("Rewrite pins")
        < step_names.index("Update dependency lock")
    )
    install = steps["Install omnibase_core handler"]
    assert install["working-directory"] == "omnibase_core"
    validator = yaml.safe_load(
        WORKFLOW.with_name("internal-sibling-pins.yml").read_text()
    )
    validator_install = next(
        s
        for s in validator["jobs"]["internal-sibling-pins"]["steps"]
        if s.get("name") == "Install the validator"
    )
    assert install["run"] == validator_install["run"]
    assert install["env"] == validator_install["env"]
    assert steps["Update dependency lock"]["working-directory"] == "downstream"
    assert (
        steps["Update dependency lock"]["run"]
        == "uv lock --upgrade-package omnibase-core"
    )
    rewrite = steps["Rewrite pins"]
    assert rewrite["working-directory"] == "omnibase_core"
    dependency, handshake = rewrite["run"].split("\nelse\n")
    assert (
        "uv run --no-sync python -m omnibase_core.nodes.node_dependency_pin_bump_effect.runtime_dependency_pin_bump"
        in dependency
    )
    assert '--dependency-tag "$DEPENDENCY_TAG"' in dependency
    assert "scripts/pin_bump.py" not in dependency
    assert "python scripts/pin_bump.py" in handshake
    assert '--new-sha "$NEW_SHA"' in handshake
    assert "--dependency-tag" not in handshake
    assert "PIN_ARGS" not in rewrite["run"]
    assert 'git commit -m "$TITLE"' in steps["Commit + push branch"]["run"]
    assert (
        steps["Mint onexbot-occ-writer app token"]["with"]["permission-workflows"]
        == "write"
    )
    assert (
        sum(s.get("name") == "Open PR + enable auto-merge" for s in bump["steps"]) == 1
    )


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["handshake", "dependency"])
def test_pr_metadata_is_parameterized_by_mode(tmp_path: Path, mode: str) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    script = next(
        s["run"]
        for s in workflow["jobs"]["bump"]["steps"]
        if s.get("name") == "Prepare PR metadata"
    )
    output = tmp_path / "env"
    sha = "a" * 40
    short = "b" * 12
    tag = f"dev-20261028010203-{short}"
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        env={
            "PATH": os.defpath,
            "GITHUB_ENV": str(output),
            "MODE": mode,
            "NEW_SHA": sha,
            "DEPENDENCY_TAG": tag,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    metadata = output.read_text()
    if mode == "dependency":
        assert f"BRANCH=bot/bump-omnibase-core-dev-pin-{short}\n" in metadata
        assert (
            f"TITLE=chore(ci): bump omnibase_core dev tag pin to {short} [bot] [OMN-21478]\n"
            in metadata
        )
        assert f"New dev tag: `{tag}`" in metadata
    else:
        assert f"BRANCH=bot/bump-omnibase-core-pin-{sha[:12]}\n" in metadata
        assert (
            f"TITLE=chore(ci): bump omnibase_core pin to {sha[:12]} [bot] [OMN-9050]\n"
            in metadata
        )
        assert f"New SHA: `{sha}`" in metadata


@pytest.mark.unit
@pytest.mark.parametrize("appears_on", [1, 3, 12, None])
def test_dev_tag_resolution_waits_for_parallel_tag_workflow(
    tmp_path: Path, appears_on: int | None
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = next(
        s
        for s in workflow["jobs"]["enumerate-repos"]["steps"]
        if s.get("name") == "Resolve dev tag"
    )
    assert step["id"] == "tag"
    assert "github.ref == 'refs/heads/dev'" in step["if"]
    assert "inputs.override_tag != ''" in step["if"]
    assert (
        step["env"]["SOURCE_URL"]
        == "${{ github.server_url }}/${{ github.repository }}.git"
    )
    sha = "a" * 40
    tag = f"dev-20261028010203-{sha[:12]}"
    (tmp_path / "reads").write_text("0\n")
    git = tmp_path / "git"
    git.write_text("""#!/bin/bash
set -euo pipefail
[[ "$*" == "ls-remote --tags $SOURCE_URL refs/tags/dev-*-${SHA:0:12}" ]]
reads=$(cat "$TEST_ROOT/reads")
reads=$((reads + 1))
echo "$reads" > "$TEST_ROOT/reads"
if [ "$reads" -ge "$APPEARS_ON" ]; then
  printf '%s\trefs/tags/%s\n' "$SHA" "$TEST_TAG"
fi
""")
    git.chmod(0o755)
    sleep = tmp_path / "sleep"
    sleep.write_text("""#!/bin/bash
[[ "$1" == "20" ]] || exit 1
echo sleep >> "$TEST_ROOT/sleeps"
""")
    sleep.chmod(0o755)
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", step["run"]],
        env={
            "PATH": str(tmp_path) + os.pathsep + os.defpath,
            "GITHUB_OUTPUT": str(output),
            "SHA": sha,
            "OVERRIDE_TAG": "",
            "SOURCE_URL": "https://git.invalid/org/repo.git",
            "TAG_WAIT_ATTEMPTS": "12",
            "TAG_WAIT_SECONDS": "20",
            "TEST_ROOT": str(tmp_path),
            "APPEARS_ON": str(appears_on or 99),
            "TEST_TAG": tag,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    attempts = appears_on or 12
    assert int((tmp_path / "reads").read_text()) == attempts
    sleeps = (
        (tmp_path / "sleeps").read_text().splitlines()
        if (tmp_path / "sleeps").exists()
        else []
    )
    assert len(sleeps) == (attempts - 1)
    if appears_on is None:
        assert result.returncode == 1
        assert (
            f"::error::No dev merge tag found for {sha} after 12 attempts"
            in result.stdout
        )
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text() == f"tag={tag}\n"


@pytest.mark.unit
def test_dev_tag_override_skips_remote_resolution(tmp_path: Path) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = next(
        s
        for s in workflow["jobs"]["enumerate-repos"]["steps"]
        if s.get("name") == "Resolve dev tag"
    )
    output = tmp_path / "output"
    tag = "dev-20261028010203-aaaaaaaaaaaa"
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env={"GITHUB_OUTPUT": str(output), "OVERRIDE_TAG": tag},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == f"tag={tag}\n"


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
