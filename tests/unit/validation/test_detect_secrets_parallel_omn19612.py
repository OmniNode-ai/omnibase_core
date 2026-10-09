# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The Detect Secrets scan fans out over the runner's cores (OMN-19612).

A pull request that edits this workflow, the secrets baseline or the scope
helper scans the whole tracked tree. Serially that took 218-285 s (run
36315033330: 285 s against a 9-13 s diff-scoped baseline), the last
quality-gate need to finish while the 40 test shards waited behind it.
detect-secrets-hook checks each file on its own, so the workflow now runs it
under ``xargs -n 100 -P "$(nproc)"``. These tests run the workflow step's own
shell with a stub hook to prove the fan-out neither drops a file nor hides a
failing chunk.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"
SCAN_FILE_COUNT = 450
FAILING_FILE = "src/pkg/mod_0420.py"

STUB_HOOK = """#!/usr/bin/env bash
# Records every scanned file it is given; fails when one is the planted secret.
status=0
for arg in "$@"; do
  case "$arg" in
    src/pkg/*)
      echo "$arg" >> "$HOOK_LOG"
      if [ "$arg" = "$PLANTED" ]; then status=1; fi
      ;;
  esac
done
exit $status
"""


def _scan_step_run() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["detect-secrets"]["steps"]
    step = next(item for item in steps if item.get("name") == "Run detect-secrets-hook")
    return str(step["run"])


def _run_scan(
    tmp_path: Path, planted: str
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    hook = bin_dir / "detect-secrets-hook"
    hook.write_text(STUB_HOOK, encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    names = [f"src/pkg/mod_{i:04d}.py" for i in range(SCAN_FILE_COUNT)]
    (runner_temp / "detect-secrets-files").write_bytes(
        b"".join(name.encode() + b"\0" for name in names)
    )
    log = tmp_path / "hook.log"
    log.write_text("", encoding="utf-8")
    env = {
        # A fixed PATH: the stub first, then the system tools xargs, nproc and bash live in.
        "PATH": f"{bin_dir}:/usr/local/bin:/usr/bin:/bin",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "HOOK_LOG": str(log),
        "PLANTED": planted,
    }
    result = subprocess.run(
        ["bash", "-e", "-c", _scan_step_run()],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, sorted(log.read_text(encoding="utf-8").split())


def test_scan_fans_out_over_the_cores_in_bounded_chunks() -> None:
    run = _scan_step_run()
    assert 'xargs -0 -r -n 100 -P "$(nproc)" detect-secrets-hook' in run
    # The same flags as before the fan-out: nothing was dropped to buy speed.
    for flag in ("--no-verify", "--baseline .secrets.baseline"):
        assert flag in run


def test_every_listed_file_is_scanned_exactly_once(tmp_path: Path) -> None:
    result, scanned = _run_scan(tmp_path, planted="none")
    assert result.returncode == 0, result.stdout + result.stderr
    assert scanned == sorted(f"src/pkg/mod_{i:04d}.py" for i in range(SCAN_FILE_COUNT))


def test_a_secret_in_any_chunk_fails_the_step(tmp_path: Path) -> None:
    """Positive control: the planted file sits in the last of five chunks."""
    result, scanned = _run_scan(tmp_path, planted=FAILING_FILE)
    assert result.returncode != 0
    assert FAILING_FILE in scanned
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "New Secrets Detected" in summary


def test_the_scan_runs_after_the_scope_step_writes_its_list() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    names = [step.get("name") for step in workflow["jobs"]["detect-secrets"]["steps"]]
    assert names.index("Decide scan scope") < names.index("Run detect-secrets-hook")
