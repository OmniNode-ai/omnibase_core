# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-22997: the ruff that checks formatting is the ruff the lock names.

The ``lint`` job of ``ci.yml`` (check name ``Code Quality``) synced and ran ruff
without ``--frozen``. Without it a pull request whose diff touches ``uv.lock``
lets uv re-resolve, so the formatter that runs is not the one the tree is
formatted for. Measured on dev at 64d60448: the
locked ruff 0.14.14 reports 8340 files already formatted, while the 0.17.4 uv
resolved on the 0.47.69 release pull request reports 9 files would be
reformatted -- a red that says nothing about the code. Only a lock-touching diff
triggers it, which is why it presented as the release pull request being cursed.

``product-readiness-shadow.yml``'s ``lint-shadow`` job carried the same shape and
reddened beside it, so it is held here too. The other unfrozen syncs in both
files run no formatter and are a separate judgement, deliberately not asserted.

These tests fail on a tree where either job omits ``--frozen``, which is what the
merge base looks like.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
SHADOW = ROOT / ".github" / "workflows" / "product-readiness-shadow.yml"


def _jobs(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


def _runs(job: dict[str, Any]) -> list[str]:
    return [str(step["run"]) for step in _steps(job) if step.get("run")]


def _code_quality_job() -> dict[str, Any]:
    named = [
        job
        for job in _jobs(CI).values()
        if isinstance(job, dict) and str(job.get("name", "")) == "Code Quality"
    ]
    assert len(named) == 1, f"expected one Code Quality job, found {len(named)}"
    return named[0]


def test_the_code_quality_sync_is_frozen() -> None:
    """An unfrozen sync resolves a ruff the lock does not name."""
    syncs = [run for run in _runs(_code_quality_job()) if "uv sync" in run]
    assert syncs, "the Code Quality job syncs nothing"
    for run in syncs:
        assert "--frozen" in run, (
            "the Code Quality job's uv sync omits --frozen, so a pull request "
            "touching uv.lock installs a formatter the tree is not formatted "
            f"for: {run!r}"
        )


def test_the_code_quality_ruff_runs_are_frozen() -> None:
    """`uv run` re-resolves too, so the flag is needed on each run."""
    ruffs = [run for run in _runs(_code_quality_job()) if "ruff" in run]
    assert len(ruffs) >= 2, f"expected the ruff format and check runs, got {ruffs!r}"
    for run in ruffs:
        assert "--frozen" in run, f"a Code Quality ruff run omits --frozen: {run!r}"


def test_no_code_quality_step_can_re_resolve_past_the_frozen_sync() -> None:
    """`uv run` resolves on its own, so one bare run undoes the frozen sync."""
    for run in _runs(_code_quality_job()):
        if not run.startswith("uv "):
            continue
        assert "--frozen" in run, (
            "a Code Quality step runs uv without --frozen, so it may re-resolve "
            f"past the frozen sync in the same job: {run!r}"
        )


def test_the_shadow_pair_is_frozen_for_the_same_reason() -> None:
    """The shadow reddened beside the required job on the same resolve."""
    job = _jobs(SHADOW)["lint-shadow"]
    runs = [run for run in _runs(job) if "ruff" in run or "uv sync" in run]
    assert len(runs) >= 3, f"expected the sync and both ruff runs, got {runs!r}"
    for run in runs:
        assert "--frozen" in run, f"a lint-shadow step omits --frozen: {run!r}"
