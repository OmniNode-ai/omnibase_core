# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-22894: security-scan.yml runs TruffleHog on a hosted runner, with a planted control.

The job is hosted in secret-scan-reusable.yml and called from security-scan.yml.

The repository is public, so the secret-scan job must run on a hosted runner. Its scanner is the
image digest the reference security-scan workflow of this organization carries (OMN-23008), spelled
here because this test cannot read another repository; the TruffleHog action only wraps a docker run
of the :latest tag, so the job runs the image by digest. The control detector must match a planted
token and must not match clean text or its own file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CALLER = REPO_ROOT / ".github" / "workflows" / "security-scan.yml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "secret-scan-reusable.yml"
CONTROL_CONFIG = REPO_ROOT / ".github" / "trufflehog-control.yml"

# The reference workflow's scanner image digest, held as its first and last characters: a whole
# 64-character hex literal reads as a secret to the repository's secret hook.
TRUFFLEHOG_IMAGE_REPO = "ghcr.io/trufflesecurity/trufflehog"
TRUFFLEHOG_DIGEST_START = "674b2f18"
TRUFFLEHOG_DIGEST_END = "46ba4a3a"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
IMAGE_REF = '"$TRUFFLEHOG_IMAGE"'
HOSTED_RUNNER = "ubuntu-latest"
CONTROL_ARGS = (
    "--config=.github/trufflehog-control.yml",
    "--include-detectors=CustomRegex",
    "--results=unverified",
    "--no-verification",
)


def _job() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    job = data["jobs"]["secret-scan"]
    assert isinstance(job, dict)
    return job


def _image() -> str:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    image = data["env"]["TRUFFLEHOG_IMAGE"]
    assert isinstance(image, str)
    return image


def _scanner_steps() -> list[dict[str, Any]]:
    return [s for s in _job()["steps"] if IMAGE_REF in str(s.get("run", ""))]


def _planted_token() -> str:
    # Built from parts so this file never holds a full control token.
    return "ONEX_SCAN_" + "CONTROL_" + "abcdefghijklmnopqrstuvwxyz012345"


def _detector_regex() -> re.Pattern[str]:
    config = yaml.safe_load(CONTROL_CONFIG.read_text(encoding="utf-8"))
    (detector,) = config["detectors"]
    assert detector["name"] == "OnexScanControl"
    return re.compile(detector["regex"]["token"])


def test_job_runs_on_a_hosted_runner_only() -> None:
    runs_on = _job()["runs-on"]
    assert runs_on == HOSTED_RUNNER
    assert "self-hosted" not in str(runs_on)
    assert "vars." not in str(runs_on)


def test_scanner_runs_the_reference_image_digest() -> None:
    repo, _, digest = _image().partition("@")
    assert repo == TRUFFLEHOG_IMAGE_REPO
    assert DIGEST.fullmatch(digest)
    assert digest.startswith("sha256:" + TRUFFLEHOG_DIGEST_START)
    assert digest.endswith(TRUFFLEHOG_DIGEST_END)
    steps = _scanner_steps()
    assert len(steps) == 3
    for step in steps:
        assert "uses" not in step
        assert ":latest" not in step["run"]
        assert "trufflesecurity/trufflehog@" not in step["run"]


def test_ordinary_scans_are_verified_only_and_the_history_is_full() -> None:
    job = _job()
    checkout = job["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 0
    ordinary = [s for s in _scanner_steps() if "--only-verified" in s["run"]]
    assert {s["name"] for s in ordinary} == {
        "TruffleHog Secret Scanning (push diff)",
        "TruffleHog Secret Scanning (full scan)",
    }
    for step in ordinary:
        assert "--fail" in step["run"]
        assert "--exclude-detectors=lob" in step["run"]


def test_control_step_reads_the_declared_detector_unverified() -> None:
    (control,) = [
        s for s in _scanner_steps() if s["name"] == "TruffleHog planted control"
    ]
    args = control["run"].replace("\\\n", " ").split()
    assert set(CONTROL_ARGS) <= set(args)
    assert "--fail" in args
    assert "--only-verified" not in args
    assert "if" not in control


def test_control_detector_matches_the_planted_token() -> None:
    assert _detector_regex().search(f"x={_planted_token()}\n")


def test_control_detector_ignores_clean_text_and_its_own_file() -> None:
    pattern = _detector_regex()
    assert not pattern.search("ONEX_SCAN_CONTROL_short")
    assert not pattern.search("a clean line with no token")
    assert not pattern.search(CONTROL_CONFIG.read_text(encoding="utf-8"))


def test_security_scan_calls_the_in_repo_reusable() -> None:
    data = yaml.safe_load(CALLER.read_text(encoding="utf-8"))
    caller = data["jobs"]["secret-scan"]
    assert caller["uses"] == "./.github/workflows/secret-scan-reusable.yml"
    assert "runs-on" not in caller
    triggers = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert set(triggers.get("on", triggers.get(True))) == {"workflow_call"}
