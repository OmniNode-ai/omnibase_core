# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The secret scan workflow: a pinned scanner, a nightly default-branch run and two controls.

Rebuild plan, step 0, safety source 1. A scanner counts as running only when a planted
credential is found and a clean file passes on every run; these tests run the workflow's own
control step against a stub scanner so each way the control can break is shown failing here,
and the real scanner is exercised in the workflow itself.
"""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
REUSABLE = REPO_ROOT / ".github" / "workflows" / "secret-scan-reusable.yml"
CALLER = REPO_ROOT / ".github" / "workflows" / "secret-scan.yml"

JOB_ID = "secret-scan"
NIGHTLY_CRON = "0 2 * * *"
IMAGE_PIN = re.compile(r"^trufflesecurity/trufflehog@sha256:[0-9a-f]{64}$")
HOSTED_LABEL = re.compile(r"^(ubuntu|windows|macos)-[\w.\-]+$", re.IGNORECASE)
# An AWS access key id as the scanner reads it: the literal must never be in the workflow.
LITERAL_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")

# Stands in for the scanner container: the exit code depends on which control mount it sees.
_STUB_DOCKER = """#!/usr/bin/env bash
case "$*" in
  */planted:/ctl*) exit "${STUB_PLANTED_RC}" ;;
  */clean:/ctl*) exit "${STUB_CLEAN_RC}" ;;
esac
exit 99
"""


def _load(path: Path = REUSABLE) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _job() -> dict[str, Any]:
    job: dict[str, Any] = _load()["jobs"][JOB_ID]
    return job


def _steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _job()["steps"]
    return steps


def _run_steps() -> list[str]:
    return [s["run"] for s in _steps() if "run" in s]


def _run_controls(tmp_path: Path, planted_rc: int, clean_rc: int) -> tuple[int, str]:
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "docker"
    stub.write_text(_STUB_DOCKER, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    env = {
        "PATH": f"{stub_dir}:/usr/local/bin:/usr/bin:/bin",
        "TRUFFLEHOG_IMAGE": _job()["env"]["TRUFFLEHOG_IMAGE"],
        "STUB_PLANTED_RC": str(planted_rc),
        "STUB_CLEAN_RC": str(clean_rc),
    }
    done = subprocess.run(
        ["bash", "-c", _run_steps()[0]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode, done.stdout + done.stderr


def test_runs_on_a_literal_hosted_label() -> None:
    runs_on = _job()["runs-on"]
    assert isinstance(runs_on, str)
    assert HOSTED_LABEL.match(runs_on)


def test_reusable_is_workflow_call_only() -> None:
    data = _load()
    assert set(data.get("on", data.get(True))) == {"workflow_call"}


def test_caller_uses_the_in_repo_reusable() -> None:
    job = _load(CALLER)["jobs"][JOB_ID]
    assert job["uses"] == "./.github/workflows/secret-scan-reusable.yml"


def test_triggers_include_the_nightly_default_branch_run() -> None:
    # PyYAML 1.1 resolves the bare `on:` key to the boolean True.
    data = _load(CALLER)
    triggers = data.get("on", data.get(True))
    assert {"push", "schedule"} <= set(triggers)
    assert {"cron": NIGHTLY_CRON} in triggers["schedule"]
    # The pull-request workflow budget refuses a new pull request workflow.
    assert "pull_request" not in triggers


def test_scanner_image_is_pinned_by_digest() -> None:
    assert IMAGE_PIN.match(_job()["env"]["TRUFFLEHOG_IMAGE"])


def test_controls_run_before_the_scan_and_the_scan_gates() -> None:
    controls, scan = _run_steps()
    assert "planted" in controls and "clean" in controls
    assert "--only-verified" in scan
    assert "--fail" in scan
    assert "|| true" not in controls
    assert "|| true" not in scan
    assert "continue-on-error" not in yaml.safe_dump(_job())


def test_no_literal_credential_is_in_the_workflow() -> None:
    assert not LITERAL_AWS_KEY.search(
        REUSABLE.read_text(encoding="utf-8") + CALLER.read_text(encoding="utf-8")
    )


def test_literal_credential_detector_has_a_positive_control() -> None:
    assert LITERAL_AWS_KEY.search("key = " + "AKIA" + "ABCDEFGHIJKLMNOP")
    assert not LITERAL_AWS_KEY.search("key = AKIA$(printf '%s' 'ABCD')")


def test_controls_pass_when_planted_is_found_and_clean_is_clean(tmp_path: Path) -> None:
    code, out = _run_controls(tmp_path, planted_rc=183, clean_rc=0)
    assert code == 0, out
    assert "scanner controls passed" in out


@pytest.mark.parametrize("blind_rc", [0, 1, 99])
def test_control_fails_when_the_scanner_misses_the_planted_credential(
    tmp_path: Path, blind_rc: int
) -> None:
    code, out = _run_controls(tmp_path, planted_rc=blind_rc, clean_rc=0)
    assert code != 0
    assert "PLANTED CONTROL FAILED" in out


def test_control_fails_when_the_scanner_flags_a_clean_file(tmp_path: Path) -> None:
    code, out = _run_controls(tmp_path, planted_rc=183, clean_rc=183)
    assert code != 0
    assert "CLEAN CONTROL FAILED" in out
