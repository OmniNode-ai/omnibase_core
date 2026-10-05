# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Retry and ``total_count`` behaviour of ``architecture-handshakes/check-policy-gate.sh``.

The gate reads the latest completed ``check-handshake.yml`` run with
``per_page=1``. A single empty page used to be a hard failure in strict mode,
which made thin repos flap. These tests drive the real script against a fake
``gh`` on PATH that serves a scripted sequence of responses per runs call.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
HANDSHAKES = REPO_ROOT / "architecture-handshakes"

# Fake gh: serves the default branch, then the Nth scripted runs response
# (the last one repeats). Each response file is JSON, or "ERR:<stderr text>"
# to emulate a failing call. --jq is applied with real jq, as gh does.
FAKE_GH = r"""#!/usr/bin/env bash
state="${FAKE_GH_STATE}"
args=("$@")
jq_expr=""
for ((i = 0; i < ${#args[@]}; i++)); do
    if [[ "${args[i]}" == "--jq" ]]; then jq_expr="${args[i+1]}"; fi
done
endpoint="${args[1]:-}"
if [[ "${endpoint}" != *"/actions/workflows/"* ]]; then
    echo main
    exit 0
fi
n=$(cat "${state}/calls" 2>/dev/null || echo 0)
echo $((n + 1)) > "${state}/calls"
total=$(ls "${state}"/resp.* | wc -l)
idx=$((n + 1 > total ? total : n + 1))
body=$(cat "${state}/resp.${idx}")
if [[ "${body}" == ERR:* ]]; then
    echo "${body#ERR:}" >&2
    exit 1
fi
printf '%s' "${body}" | jq -r "${jq_expr}"
"""


def _run_resp(conclusion: str | None, total: int) -> str:
    runs = [] if conclusion is None else [{"conclusion": conclusion}]
    return json.dumps({"total_count": total, "workflow_runs": runs})


def _run_gate(
    tmp_path: Path,
    responses: list[str],
    *extra_args: str,
    base_delay: str = "0",
) -> tuple[subprocess.CompletedProcess[str], int]:
    script_dir = tmp_path / "hs"
    script_dir.mkdir()
    for name in ("check-policy-gate.sh", "_parse_repos_conf.sh"):
        shutil.copy(HANDSHAKES / name, script_dir / name)
    (script_dir / "repos.conf").write_text("thinrepo\n")

    state = tmp_path / "state"
    state.mkdir()
    for i, body in enumerate(responses, start=1):
        (state / f"resp.{i}").write_text(body)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "FAKE_GH_STATE": str(state),
        "GH_TOKEN": "fake",
        "POLICY_GATE_RETRY_BASE_DELAY": base_delay,
    }
    proc = subprocess.run(
        ["bash", str(script_dir / "check-policy-gate.sh"), "--strict", *extra_args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    calls = int((state / "calls").read_text()) if (state / "calls").exists() else 0
    return proc, calls


def test_success_first_try_makes_one_runs_call(tmp_path: Path) -> None:
    proc, calls = _run_gate(tmp_path, [_run_resp("success", 5)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls == 1


def test_empty_page_then_runs_retries_and_passes(tmp_path: Path) -> None:
    # An empty page while total_count says runs exist is transient, not a failure.
    proc, calls = _run_gate(
        tmp_path, [_run_resp(None, 3), _run_resp(None, 3), _run_resp("success", 3)]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls == 3


def test_transient_api_error_then_success_passes(tmp_path: Path) -> None:
    proc, calls = _run_gate(
        tmp_path, ["ERR:HTTP 502 Bad Gateway", _run_resp("success", 2)]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls == 2


def test_genuinely_zero_runs_fails_clearly(tmp_path: Path) -> None:
    proc, _ = _run_gate(tmp_path, [_run_resp(None, 0)])
    assert proc.returncode == 1
    assert "has no runs" in proc.stdout
    assert "POLICY GATE: FAILED" in proc.stdout


def test_persistent_empty_page_with_runs_is_error_not_no_runs(tmp_path: Path) -> None:
    proc, calls = _run_gate(tmp_path, [_run_resp(None, 3)])
    assert proc.returncode == 1
    assert "has no runs" not in proc.stdout
    assert "API error" in proc.stdout
    assert calls == 4


def test_persistent_api_error_fails_after_retries(tmp_path: Path) -> None:
    proc, calls = _run_gate(tmp_path, ["ERR:HTTP 500 Server Error"])
    assert proc.returncode == 1
    assert "API error" in proc.stdout
    assert calls == 4


def test_404_is_no_workflow_without_retry(tmp_path: Path) -> None:
    proc, calls = _run_gate(tmp_path, ["ERR:HTTP 404: Not Found"])
    assert proc.returncode == 1
    assert "no check-handshake workflow found" in proc.stdout
    assert calls == 1


def test_real_failure_conclusion_is_not_retried(tmp_path: Path) -> None:
    proc, calls = _run_gate(tmp_path, [_run_resp("failure", 4)])
    assert proc.returncode == 1
    assert "workflow failing" in proc.stdout
    assert calls == 1


def test_fractional_base_delay_does_not_abort_the_gate(tmp_path: Path) -> None:
    # Integer-only backoff arithmetic must not kill the script under set -e.
    proc, calls = _run_gate(
        tmp_path,
        ["ERR:HTTP 502 Bad Gateway", _run_resp("success", 2)],
        base_delay="0.5",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls == 2
