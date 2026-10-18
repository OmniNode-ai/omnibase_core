# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19998: the heavy test suites run once per change, not once per event.

``.github/workflows/full-suite-reuse.yml`` reports ``reuse=true`` only when a
full-suite pass marker for the exact tree this run tests was uploaded by a run
of a head this event lands. ``ci.yml`` skips both test matrices on reuse,
``Tests Gate`` admits that skip only with a named producing run, and
``full-suite-pass-marker`` uploads the marker only after a full pass.

The probe's shell runs here against a fake ``gh`` that answers each API path
from a fixture table, so every refusal arm is exercised, not only read.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REUSE_PATH = REPO_ROOT / ".github" / "workflows" / "full-suite-reuse.yml"

REPO = "OmniNode-ai/omnibase_core"
RUN_ID = "900"
SHA = "a" * 40
TREE = "b" * 40
PR_HEAD = "c" * 40
OTHER_HEAD = "d" * 40
CI_PATH_VALUE = ".github/workflows/ci.yml"

FAKE_GH = """#!{python}
import json, os, sys
args = sys.argv[1:]
if not args or args[0] != "api":
    sys.exit(2)
table = json.load(open(os.environ["FAKE_GH_TABLE"]))
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(args[1] + "\\n")
answer = table.get(args[1])
if answer is None:
    sys.stderr.write("HTTP 404: " + args[1] + "\\n")
    sys.exit(1)
sys.stdout.write(answer)
"""


def _workflow(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict)
    return data


def _jobs(path: Path) -> dict[str, dict[str, object]]:
    jobs = _workflow(path)["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _probe_script() -> str:
    steps = _jobs(REUSE_PATH)["probe"]["steps"]
    assert isinstance(steps, list)
    return str(steps[0]["run"])


def _base_table() -> dict[str, str]:
    return {
        f"repos/{REPO}/git/commits/{SHA}": TREE + "\n",
        f"repos/{REPO}/actions/runs/{RUN_ID}": CI_PATH_VALUE + "\n",
    }


def _markers_key() -> str:
    return f"repos/{REPO}/actions/artifacts?name=full-suite-pass-{TREE}&per_page=100"


def _run_probe(
    tmp_path: Path,
    table: dict[str, str],
    *,
    event: str,
    pr_head: str = "",
    merge_group_ref: str = "",
) -> tuple[dict[str, str], str, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH.replace("{python}", sys.executable))
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    table_path = tmp_path / "table.json"
    table_path.write_text(json.dumps(table))
    log_path = tmp_path / "gh.log"
    log_path.write_text("")
    out_path = tmp_path / "out.txt"
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "FAKE_GH_TABLE": str(table_path),
        "FAKE_GH_LOG": str(log_path),
        "GITHUB_OUTPUT": str(out_path),
        "REPO": REPO,
        "EVENT_NAME": event,
        "RUN_SHA": SHA,
        "RUN_ID": RUN_ID,
        "PR_HEAD_SHA": pr_head,
        "MERGE_GROUP_HEAD_REF": merge_group_ref,
        "ARTIFACT_PREFIX": "full-suite-pass",
    }
    proc = subprocess.run(
        ["bash", "-c", _probe_script()],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    outputs = dict(
        line.split("=", 1) for line in out_path.read_text().splitlines() if line
    )
    return outputs, proc.stdout, log_path.read_text().splitlines()


def test_push_reuses_the_merge_group_run_of_the_same_commit(tmp_path: Path) -> None:
    table = _base_table()
    table[f"repos/{REPO}/commits/{SHA}/pulls"] = PR_HEAD + "\n"
    table[_markers_key()] = f"777 {SHA}\n"
    table[f"repos/{REPO}/actions/runs/777"] = CI_PATH_VALUE + "\n"
    outputs, _, _ = _run_probe(tmp_path, table, event="push")
    assert outputs == {"tree": TREE, "reuse": "true", "producer_run": "777"}


def test_merge_group_reuses_the_queued_pull_request_head(tmp_path: Path) -> None:
    table = _base_table()
    table[f"repos/{REPO}/pulls/42"] = PR_HEAD + "\n"
    table[_markers_key()] = f"555 {PR_HEAD}\n"
    table[f"repos/{REPO}/actions/runs/555"] = CI_PATH_VALUE + "\n"
    ref = f"refs/heads/gh-readonly-queue/dev/pr-42-{'e' * 40}"
    outputs, _, _ = _run_probe(
        tmp_path, table, event="merge_group", merge_group_ref=ref
    )
    assert outputs["reuse"] == "true"
    assert outputs["producer_run"] == "555"


def test_marker_from_another_head_is_refused(tmp_path: Path) -> None:
    """A run of a different pull request that uploaded a marker for this tree
    did not test this event's head: no reuse."""
    table = _base_table()
    table[f"repos/{REPO}/pulls/42"] = PR_HEAD + "\n"
    table[_markers_key()] = f"555 {OTHER_HEAD}\n"
    table[f"repos/{REPO}/actions/runs/555"] = CI_PATH_VALUE + "\n"
    ref = f"refs/heads/gh-readonly-queue/dev/pr-42-{'e' * 40}"
    outputs, stdout, _ = _run_probe(
        tmp_path, table, event="merge_group", merge_group_ref=ref
    )
    assert outputs["reuse"] == "false"
    assert outputs["producer_run"] == ""
    assert "not a head of this event" in stdout


def test_marker_from_another_workflow_is_refused(tmp_path: Path) -> None:
    table = _base_table()
    table[_markers_key()] = f"555 {PR_HEAD}\n"
    table[f"repos/{REPO}/actions/runs/555"] = ".github/workflows/other.yml\n"
    outputs, stdout, _ = _run_probe(
        tmp_path, table, event="pull_request", pr_head=PR_HEAD
    )
    assert outputs["reuse"] == "false"
    assert "not .github/workflows/ci.yml" in stdout


def test_own_run_marker_is_not_reused(tmp_path: Path) -> None:
    table = _base_table()
    table[_markers_key()] = f"{RUN_ID} {PR_HEAD}\n"
    outputs, _, _ = _run_probe(tmp_path, table, event="pull_request", pr_head=PR_HEAD)
    assert outputs["reuse"] == "false"


def test_pull_request_rerun_on_the_same_head_reuses(tmp_path: Path) -> None:
    table = _base_table()
    table[_markers_key()] = f"555 {PR_HEAD}\n"
    table[f"repos/{REPO}/actions/runs/555"] = CI_PATH_VALUE + "\n"
    outputs, _, _ = _run_probe(tmp_path, table, event="pull_request", pr_head=PR_HEAD)
    assert outputs["reuse"] == "true"


def test_no_marker_runs_the_suite(tmp_path: Path) -> None:
    table = _base_table()
    table[_markers_key()] = ""
    outputs, stdout, _ = _run_probe(
        tmp_path, table, event="pull_request", pr_head=PR_HEAD
    )
    assert outputs["reuse"] == "false"
    assert "reason=no-marker" in stdout


@pytest.mark.parametrize("missing", ["tree", "markers", "own_run"])
def test_every_lookup_failure_runs_the_suite(tmp_path: Path, missing: str) -> None:
    table = _base_table()
    table[_markers_key()] = f"555 {PR_HEAD}\n"
    table[f"repos/{REPO}/actions/runs/555"] = CI_PATH_VALUE + "\n"
    key = {
        "tree": f"repos/{REPO}/git/commits/{SHA}",
        "markers": _markers_key(),
        "own_run": f"repos/{REPO}/actions/runs/{RUN_ID}",
    }[missing]
    del table[key]
    outputs, stdout, _ = _run_probe(
        tmp_path, table, event="pull_request", pr_head=PR_HEAD
    )
    assert outputs["reuse"] == "false"
    assert "unreadable" in stdout


@pytest.mark.parametrize("event", ["schedule", "workflow_dispatch"])
def test_scheduled_and_dispatched_runs_never_reuse(tmp_path: Path, event: str) -> None:
    table = _base_table()
    table[_markers_key()] = f"555 {SHA}\n"
    table[f"repos/{REPO}/actions/runs/555"] = CI_PATH_VALUE + "\n"
    outputs, _, calls = _run_probe(tmp_path, table, event=event)
    assert outputs["reuse"] == "false"
    assert _markers_key() not in calls


def test_jq_filters_select_what_the_probe_reads() -> None:
    """The fake gh above answers post-jq text; prove the real jq filters
    produce that text from the API's own response shapes."""
    script = _probe_script()
    artifacts = {
        "artifacts": [
            {"expired": False, "workflow_run": {"id": 555, "head_sha": PR_HEAD}},
            {"expired": True, "workflow_run": {"id": 556, "head_sha": PR_HEAD}},
        ]
    }
    artifact_filter = (
        ".artifacts[] | select(.expired == false) | "
        '"\\(.workflow_run.id) \\(.workflow_run.head_sha)"'
    )
    assert artifact_filter in script
    got = subprocess.run(
        ["jq", "-r", artifact_filter],
        input=json.dumps(artifacts),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert got == f"555 {PR_HEAD}\n"

    pulls = [
        {"merge_commit_sha": SHA, "head": {"sha": PR_HEAD}},
        {"merge_commit_sha": "f" * 40, "head": {"sha": OTHER_HEAD}},
    ]
    pulls_filter = f'.[] | select(.merge_commit_sha == "{SHA}") | .head.sha'
    assert '.[] | select(.merge_commit_sha == \\"$RUN_SHA\\") | .head.sha' in script
    got = subprocess.run(
        ["jq", "-r", pulls_filter],
        input=json.dumps(pulls),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert got == f"{PR_HEAD}\n"


def test_ci_calls_the_probe_and_both_matrices_skip_only_on_reuse() -> None:
    jobs = _jobs(CI_PATH)
    assert (
        jobs["full-suite-reuse"]["uses"] == "./.github/workflows/full-suite-reuse.yml"
    )
    for job_id in ("test-parallel", "tests-integration", "shadow-compare"):
        assert "full-suite-reuse" in jobs[job_id]["needs"]
        assert "needs.full-suite-reuse.outputs.reuse != 'true'" in str(
            jobs[job_id]["if"]
        )


def test_tests_gate_admits_a_reuse_skip_only_with_a_named_producer() -> None:
    gate = _jobs(CI_PATH)["tests-gate"]
    assert "full-suite-reuse" in gate["needs"]
    run = str(gate["steps"][0]["run"])
    assert (
        'if [ "$reuse" = "true" ] && [ -n "$reuse_run" ] && [ "$quality" = "success" ]'
        in run
    )


def test_marker_is_uploaded_only_after_a_full_pass_or_a_verified_reuse() -> None:
    marker = _jobs(CI_PATH)["full-suite-pass-marker"]
    assert marker["uses"] == "./.github/workflows/full-suite-reuse.yml"
    assert "needs.tests-gate.result == 'success'" in str(marker["if"])
    assert marker["with"]["mode"] == "mark"
    eligible = " ".join(str(marker["with"]["eligible"]).split())
    assert "needs.full-suite-reuse.outputs.reuse == 'true'" in eligible
    assert "needs.detect-changes.outputs.is_full_suite == 'true'" in eligible
    assert "needs.test-parallel.result == 'success'" in eligible
    assert "needs.tests-integration.result == 'success'" in eligible


def _mark_script() -> str:
    steps = _jobs(REUSE_PATH)["mark"]["steps"]
    assert isinstance(steps, list)
    return str(steps[0]["run"])


@pytest.mark.parametrize(
    ("eligible", "tree", "upload"),
    [("true", TREE, "true"), ("false", TREE, "false"), ("true", "", "false")],
)
def test_mark_uploads_only_an_eligible_tree(
    tmp_path: Path, eligible: str, tree: str, upload: str
) -> None:
    out_path = tmp_path / "out.txt"
    env = {
        "PATH": "/usr/bin:/bin",
        "GITHUB_OUTPUT": str(out_path),
        "GITHUB_SHA": SHA,
        "GITHUB_RUN_ID": RUN_ID,
        "GITHUB_EVENT_NAME": "merge_group",
        "TREE": tree,
        "ELIGIBLE": eligible,
        "REUSED_FROM": "",
    }
    proc = subprocess.run(
        ["bash", "-c", _mark_script()],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert f"upload={upload}" in out_path.read_text()
    marker = tmp_path / "full-suite-pass.json"
    assert marker.exists() is (upload == "true")
    if upload == "true":
        assert json.loads(marker.read_text())["tree"] == TREE
    upload_step = _jobs(REUSE_PATH)["mark"]["steps"][-1]
    assert upload_step["if"] == "steps.marker.outputs.upload == 'true'"
    assert upload_step["with"]["name"] == (
        "${{ inputs.artifact-prefix }}-${{ inputs.tree }}"
    )
