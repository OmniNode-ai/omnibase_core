# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The forty test splits restore the pinned yamlfmt from a cache before any download.

The dev schedule run 42578572957 (head cd128b790, 2026-11-09T07:19Z) and the
release PR run 42578595042 each lost four of the forty ``Tests (Split N/40)``
jobs after 102 to 110 seconds, against 20 to 30 minutes for the splits that ran.
That duration is what ``Install pinned yamlfmt`` spends when every attempt of
its ``curl --retry 8 --retry-delay 10`` fails: eight 10 s waits plus the checkout
and ``uv sync`` before it. The step's retry window was already widened once
(``test_yamlfmt_download_retry_window_omn17427.py``) and a longer window only
moves the line: all forty splits still fetch the same release asset from
github.com within the same minute on every run. The step therefore restores the
binary from ``actions/cache`` and downloads only on a miss.

The checks read the workflow the way CI runs it. ``violations`` returns every
way the cache-first shape can be broken, and the injected breaks below each
have to produce at least one of them, so a green reading cannot come from a
check that never looks.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

CI_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
JOB_ID = "test-parallel"
INSTALL_STEP = "Install pinned yamlfmt"
CACHE_ACTION_PREFIX = "actions/cache@"
PATH_STEP_MARKER = "GITHUB_PATH"


def _load() -> dict[str, Any]:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def _steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return workflow["jobs"][JOB_ID]["steps"]


def _index(steps: list[dict[str, Any]], name: str) -> int:
    (found,) = [i for i, s in enumerate(steps) if s.get("name") == name]
    return found


def violations(workflow: dict[str, Any]) -> list[str]:
    """Every way the test splits' yamlfmt install is not cache-first."""
    steps = _steps(workflow)
    problems: list[str] = []
    install_at = _index(steps, INSTALL_STEP)
    install = steps[install_at]

    caches = [
        (i, s)
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith(CACHE_ACTION_PREFIX)
        and "yamlfmt" in str(s.get("with", {}).get("path", ""))
    ]
    if len(caches) != 1:
        return [f"expected one yamlfmt actions/cache step, found {len(caches)}"]
    cache_at, cache = caches[0]
    cache_id = cache.get("id")

    if cache_at >= install_at:
        problems.append("the cache restore must run before the download step")
    if not cache_id:
        problems.append("the cache step needs an id so the download can read cache-hit")
    elif f"steps.{cache_id}.outputs.cache-hit" not in str(install.get("if", "")):
        problems.append("the download step must run only on a cache miss")

    version = re.search(r"yamlfmt_([0-9.]+)_Linux", install["run"])
    key = str(cache.get("with", {}).get("key", ""))
    if version is None:
        problems.append("the download step names no pinned yamlfmt version")
    elif version.group(1) not in key:
        problems.append(f"the cache key {key!r} must carry version {version.group(1)}")
    if "runner.arch" not in key:
        problems.append(
            "the cache key must carry runner.arch: the asset differs per arch"
        )

    path_steps = [
        s for s in steps[install_at + 1 :] if PATH_STEP_MARKER in str(s.get("run", ""))
    ]
    if len(path_steps) != 1:
        problems.append("one step after the download must put yamlfmt on PATH")
    elif "if" in path_steps[0]:
        problems.append("putting yamlfmt on PATH must run on a hit and on a miss")
    if PATH_STEP_MARKER in install["run"]:
        problems.append(
            "the download step must leave PATH to the step that runs on a hit"
        )
    return problems


def test_test_splits_restore_yamlfmt_from_cache_before_downloading() -> None:
    assert violations(_load()) == []


def _without_cache_step(workflow: dict[str, Any]) -> None:
    steps = _steps(workflow)
    steps[:] = [
        s
        for s in steps
        if not str(s.get("uses", "")).startswith(CACHE_ACTION_PREFIX)
        or "yamlfmt" not in str(s.get("with", {}).get("path", ""))
    ]


def _download_unconditional(workflow: dict[str, Any]) -> None:
    _steps(workflow)[_index(_steps(workflow), INSTALL_STEP)].pop("if", None)


def _key_without_arch(workflow: dict[str, Any]) -> None:
    for step in _steps(workflow):
        if str(step.get("uses", "")).startswith(
            CACHE_ACTION_PREFIX
        ) and "yamlfmt" in str(step["with"]["path"]):
            step["with"]["key"] = "yamlfmt-0.21.0"


def _path_only_on_miss(workflow: dict[str, Any]) -> None:
    steps = _steps(workflow)
    for step in steps[_index(steps, INSTALL_STEP) + 1 :]:
        if PATH_STEP_MARKER in str(step.get("run", "")):
            step["if"] = "steps.yamlfmt-cache.outputs.cache-hit != 'true'"
            return


def _cache_after_download(workflow: dict[str, Any]) -> None:
    steps = _steps(workflow)
    cache_at = next(
        i
        for i, s in enumerate(steps)
        if str(s.get("uses", "")).startswith(CACHE_ACTION_PREFIX)
        and "yamlfmt" in str(s.get("with", {}).get("path", ""))
    )
    steps.insert(_index(steps, INSTALL_STEP) + 1, steps.pop(cache_at))


INJECTED_BREAKS = {
    "no-cache-step": _without_cache_step,
    "download-on-every-run": _download_unconditional,
    "key-without-arch": _key_without_arch,
    "path-only-on-a-miss": _path_only_on_miss,
    "cache-after-download": _cache_after_download,
}


@pytest.mark.parametrize("name", sorted(INJECTED_BREAKS))
def test_each_injected_break_is_read_as_a_violation(name: str) -> None:
    broken = copy.deepcopy(_load())
    INJECTED_BREAKS[name](broken)
    assert violations(broken), f"injected break {name!r} was not detected"
