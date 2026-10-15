# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The pinned yamlfmt download in the test splits outlasts a short upstream 504.

The dev push CI run 38784521172 (head 2351a6c6, 2026-10-15T18:18:26Z) went red
because two of the forty test splits, 11 and 24, failed at "Install pinned
yamlfmt": the GitHub release download answered HTTP 504 on all four attempts of
``curl --retry 3``, whose default backoff (1 s, 2 s, 4 s) gives up after about
seven seconds. No test ran in either split, and the same step passed on all
forty splits of the next run. A post-merge red like this one is invisible on
pull requests, so the download carries a fixed retry delay and a total budget
long enough to ride out a gateway blip of a minute (OMN-17427).
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

CI_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
STEP_NAME = "Install pinned yamlfmt"
MIN_RETRY_WAIT_SECONDS = 60
MIN_RETRY_MAX_TIME_SECONDS = 120


def _yamlfmt_curl_argv() -> list[str]:
    workflow: dict[str, Any] = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test-parallel"]["steps"]
    (step,) = [s for s in steps if s.get("name") == STEP_NAME]
    script = step["run"].replace("\\\n", " ")
    (curl_line,) = [
        line for line in script.splitlines() if line.strip().startswith("curl ")
    ]
    return shlex.split(curl_line)


def _int_flag(argv: list[str], flag: str) -> int:
    assert flag in argv, f"{STEP_NAME} curl is missing {flag}: {argv}"
    return int(argv[argv.index(flag) + 1])


def test_yamlfmt_download_waits_out_a_minute_long_upstream_failure() -> None:
    argv = _yamlfmt_curl_argv()
    retries = _int_flag(argv, "--retry")
    delay = _int_flag(argv, "--retry-delay")
    assert retries * delay >= MIN_RETRY_WAIT_SECONDS, (
        f"{STEP_NAME} retries for {retries * delay}s in total; the 504 that "
        f"turned dev red outlasted curl's default seven-second backoff"
    )


def test_yamlfmt_download_has_a_bounded_total_retry_budget() -> None:
    argv = _yamlfmt_curl_argv()
    max_time = _int_flag(argv, "--retry-max-time")
    assert max_time >= MIN_RETRY_MAX_TIME_SECONDS
    # A budget the job timeout dwarfs: the download never eats the split.
    assert max_time <= 300
