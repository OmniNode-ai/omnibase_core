# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Executable fail-closed coverage for OMN-18157's two-checkout CI binding."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
RESOLVER = REPO_ROOT / "scripts/ci/resolve_contract_compliance_evidence.py"
RUNNER = REPO_ROOT / "scripts/ci/run_contract_compliance_with_evidence.py"
CI_YML = REPO_ROOT / ".github/workflows/ci.yml"


@pytest.fixture
def fake_bin(tmp_path: Path) -> Path:
    """A deterministic gh stub; its behavior is selected through GH_CASE."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
args="$*"
case "${GH_CASE:-}" in
  valid)
    if [[ "$args" == *"pr view 7 --repo OmniNode-ai/omnibase_core --json body"* ]]; then
      printf '%s\\n' '{"body":"Evidence-Source: OCC#99"}'
    elif [[ "$args" == *"pr view 99 --repo OmniNode-ai/onex_change_control"* ]]; then
      printf '%s\\n' '{"state":"OPEN","headRefOid":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","mergeCommit":null}'
    else
      echo "unexpected gh invocation: $args" >&2; exit 8
    fi
    ;;
  missing)
    printf '%s\\n' '{"body":"No evidence source"}'
    ;;
  malformed)
    printf '%s\\n' '{"body":"Evidence-Source: not-a-reference!"}'
    ;;
  closed)
    if [[ "$args" == *"--json body"* ]]; then
      printf '%s\\n' '{"body":"Evidence-Source: OCC#99"}'
    else
      printf '%s\\n' '{"state":"CLOSED","headRefOid":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","mergeCommit":null}'
    fi
    ;;
  unresolved-push)
    echo 'gh unavailable' >&2; exit 1
    ;;
  *)
    echo "unknown GH_CASE=${GH_CASE:-}" >&2; exit 9
    ;;
esac
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    return bindir


def _env(fake_bin: Path, **values: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env.update(values)
    return env


def _resolve(
    tmp_path: Path, fake_bin: Path, *, case: str, event: str = "pull_request"
) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "github-output"
    return subprocess.run(
        [
            sys.executable,
            str(RESOLVER),
            "--repo",
            "OmniNode-ai/omnibase_core",
            "--event-name",
            event,
            "--commit-sha",
            "b" * 40,
            "--pr-number",
            "7" if event == "pull_request" else "",
        ],
        env=_env(fake_bin, GH_CASE=case, GITHUB_OUTPUT=str(output)),
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_evidence_source_resolves_an_immutable_data_sha(
    tmp_path: Path, fake_bin: Path
) -> None:
    result = _resolve(tmp_path, fake_bin, case="valid")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "github-output").read_text(encoding="utf-8") == (
        "pr_number=7\nocc_sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
    )


def test_missing_or_malformed_evidence_source_fails_without_fallback(
    tmp_path: Path, fake_bin: Path
) -> None:
    for case in ("missing", "malformed"):
        result = _resolve(tmp_path, fake_bin, case=case)
        assert result.returncode == 1
        assert "evidence" in result.stderr.lower()


def test_closed_unmerged_occ_reference_fails(tmp_path: Path, fake_bin: Path) -> None:
    result = _resolve(tmp_path, fake_bin, case="closed")
    assert result.returncode == 1
    assert "require OPEN or MERGED" in result.stderr


def test_unavailable_push_and_merge_group_pr_resolution_fail(
    tmp_path: Path, fake_bin: Path
) -> None:
    for event in ("push", "merge_group"):
        result = _resolve(tmp_path, fake_bin, case="unresolved-push", event=event)
        assert result.returncode == 1
        assert "resolution failed" in result.stderr


def _make_checker(tmp_path: Path) -> Path:
    checker = tmp_path / "checker"
    module = checker / "src/onex_change_control/scripts"
    module.mkdir(parents=True)
    for package in (
        checker / "src/onex_change_control/__init__.py",
        checker / "src/onex_change_control/scripts/__init__.py",
    ):
        package.write_text("", encoding="utf-8")
    (module / "contract_compliance_check.py").write_text(
        "def _extract_ticket_id(pr_number, repo):\n    return 'OMN-18157'\n",
        encoding="utf-8",
    )
    script = checker / "scripts/ci/run_contract_compliance_check.py"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    allowlist = checker / "scripts/ci/dod_runner_legacy_allowlist.txt"
    allowlist.write_text("", encoding="utf-8")
    return checker


def _runner_command(checker: Path, evidence: Path, workspace: Path) -> list[str]:
    return [
        sys.executable,
        str(RUNNER),
        "--pr",
        "7",
        "--repo",
        "OmniNode-ai/omnibase_core",
        "--checker-dir",
        str(checker),
        "--evidence-contracts-dir",
        str(evidence),
        "--workspace",
        str(workspace),
        "--legacy-allowlist",
        str(checker / "scripts/ci/dod_runner_legacy_allowlist.txt"),
    ]


def test_missing_data_contract_fails_before_uv_runner(
    tmp_path: Path, fake_bin: Path
) -> None:
    checker = _make_checker(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    log = tmp_path / "uv.log"
    uv = fake_bin / "uv"
    uv.write_text(f"#!/usr/bin/env bash\nprintf invoked > {log}\n", encoding="utf-8")
    uv.chmod(0o755)
    result = subprocess.run(
        _runner_command(checker, evidence, tmp_path),
        env=_env(fake_bin),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "lacks the resolved ticket contract" in result.stderr
    assert not log.exists()


def test_valid_evidence_invokes_pinned_runner_with_data_and_workspace(
    tmp_path: Path, fake_bin: Path
) -> None:
    checker = _make_checker(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "OMN-18157.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    log = tmp_path / "uv.log"
    uv = fake_bin / "uv"
    uv.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$PWD|$*\" > {log}\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    workspace = tmp_path / "product"
    workspace.mkdir()
    result = subprocess.run(
        _runner_command(checker, evidence, workspace),
        env=_env(fake_bin),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    invocation = log.read_text(encoding="utf-8")
    assert str(checker) in invocation
    assert f"--contracts-dir {evidence}" in invocation
    assert f"--workspace {workspace}" in invocation


def test_workflow_keeps_checker_pin_and_uses_separate_evidence_checkout() -> None:
    workflow = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["contract-compliance"]["steps"]
    checkouts = [
        step
        for step in steps
        if step.get("uses") == "actions/checkout@v7" and "with" in step
    ]
    checker = next(
        step
        for step in checkouts
        if step["with"].get("path") == "onex_change_control_checker"
    )
    evidence = next(
        step
        for step in checkouts
        if step["with"].get("path") == "onex_change_control_evidence"
    )
    assert checker["with"]["ref"] == "91f5b69104366c2d86e4bb21de67c3c497702111"
    assert (
        evidence["with"]["ref"]
        == "${{ steps.resolve_contract_compliance_evidence.outputs.occ_sha }}"
    )
    run_step = next(
        step
        for step in steps
        if step.get("name")
        == "Run DoD contract compliance against the product tree (OMN-14887)"
    )
    assert "run_contract_compliance_with_evidence.py" in run_step["run"]
    assert (
        "steps.resolve_contract_compliance_evidence.outputs.pr_number"
        in run_step["run"]
    )
    assert "$GITHUB_WORKSPACE/onex_change_control_evidence/contracts" in run_step["run"]
    assert '--workspace "$GITHUB_WORKSPACE"' in run_step["run"]
    assert (
        "onex_change_control_checker/scripts/ci/dod_runner_legacy_allowlist.txt"
        in run_step["run"]
    )
    receipt_gate = (REPO_ROOT / ".github/workflows/receipt-gate.yml").read_text(
        encoding="utf-8"
    )
    assert 'elif [ "$occ_state" = "OPEN" ]; then' in receipt_gate
    assert "references require OPEN or MERGED" in receipt_gate
