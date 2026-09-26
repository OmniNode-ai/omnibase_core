# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pin the anti-growth baseline hook and reusable caller contract (OMN-19677)."""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
SKIP_FILE = REPO_ROOT / ".github" / "precommit-suite-skip.yaml"

JOB_ID = "pydantic-extra-forbid-baseline-oneway"
PRECOMMIT_SUITE_JOB_ID = "precommit-suite"
HOOK_ID = "anti-growth-baseline"
OMNICLAUDE_REPO = "https://github.com/OmniNode-ai/omniclaude"
REUSABLE_PREFIX = (
    "OmniNode-ai/omniclaude/.github/workflows/anti-growth-baseline-reusable.yml@"
)
GATE_JOB_NAME = (
    'Pydantic extra="forbid" Baseline One-way (OMN-19677) / anti-growth-baseline'
)


def _mapping(value: object, label: str) -> dict[str, Any]:
    assert isinstance(value, dict), f"{label} must be a mapping"
    return cast(dict[str, Any], value)


def _sequence(value: object, label: str) -> list[Any]:
    assert isinstance(value, list), f"{label} must be a list"
    return value


def _load_mapping(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path.name)


def _workflow_job(job_id: str) -> dict[str, Any]:
    jobs = _mapping(_load_mapping(CI_WORKFLOW).get("jobs"), "ci.yml jobs")
    return _mapping(jobs.get(job_id), f"ci.yml job {job_id}")


def _hook_repo() -> dict[str, Any]:
    config = _load_mapping(PRECOMMIT_CONFIG)
    matches: list[dict[str, Any]] = []
    for repo_value in _sequence(config.get("repos"), "pre-commit repos"):
        repo = _mapping(repo_value, "pre-commit repo")
        if repo.get("repo") != OMNICLAUDE_REPO:
            continue
        hooks = _sequence(repo.get("hooks"), "pre-commit hooks")
        hook_ids = {_mapping(hook, "pre-commit hook").get("id") for hook in hooks}
        if HOOK_ID in hook_ids:
            matches.append(repo)

    assert len(matches) == 1, (
        f"expected exactly one {OMNICLAUDE_REPO} entry containing {HOOK_ID}, "
        f"found {len(matches)}"
    )
    return matches[0]


def _hook() -> dict[str, Any]:
    hooks = _sequence(_hook_repo().get("hooks"), "anti-growth hook list")
    matches = [
        _mapping(hook, "pre-commit hook")
        for hook in hooks
        if _mapping(hook, "pre-commit hook").get("id") == HOOK_ID
    ]
    assert len(matches) == 1, f"expected exactly one {HOOK_ID} hook"
    return matches[0]


def _hook_args() -> list[str]:
    args = _sequence(_hook().get("args"), f"{HOOK_ID} args")
    assert all(isinstance(arg, str) for arg in args), "hook args must be strings"
    return cast(list[str], args)


def _arg_value(flag: str) -> str:
    args = _hook_args()
    assert args.count(flag) == 1, f"expected exactly one {flag} hook argument"
    index = args.index(flag)
    assert index + 1 < len(args), f"{flag} has no value"
    return args[index + 1]


def _workflow_sha() -> str:
    uses = _workflow_job(JOB_ID).get("uses")
    assert isinstance(uses, str), f"{JOB_ID}.uses must be a string"
    match = re.fullmatch(rf"{re.escape(REUSABLE_PREFIX)}([0-9a-f]{{40}})", uses)
    assert match is not None, (
        f"{JOB_ID}.uses must call the anti-growth reusable at an immutable SHA"
    )
    return match.group(1)


def test_reusable_workflow_is_pinned_to_an_immutable_sha() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", _workflow_sha()) is not None


def test_hook_and_reusable_workflow_share_one_pin() -> None:
    revision = _hook_repo().get("rev")
    assert isinstance(revision, str), "omniclaude hook rev must be a string"
    assert _workflow_sha() == revision


def test_reusable_inputs_match_hook_baseline_and_parser_args() -> None:
    inputs = _mapping(_workflow_job(JOB_ID).get("with"), f"{JOB_ID}.with")
    assert inputs.get("baseline-path") == _arg_value("--baseline")
    assert inputs.get("parser") == _arg_value("--parser")


def test_reusable_receives_only_declared_inputs() -> None:
    inputs = _mapping(_workflow_job(JOB_ID).get("with"), f"{JOB_ID}.with")
    assert set(inputs) == {"baseline-path", "parser"}


def test_precommit_suite_runs_hook_with_origin_dev_available() -> None:
    skipped = _sequence(yaml.safe_load(SKIP_FILE.read_text(encoding="utf-8")), "skips")
    assert HOOK_ID not in skipped

    steps = _sequence(
        _workflow_job(PRECOMMIT_SUITE_JOB_ID).get("steps"),
        f"{PRECOMMIT_SUITE_JOB_ID}.steps",
    )
    checkouts = [
        _mapping(step, "precommit-suite step")
        for step in steps
        if _mapping(step, "precommit-suite step").get("name") == "Checkout code"
    ]
    assert len(checkouts) == 1, "precommit-suite must have one Checkout code step"
    checkout = checkouts[0]
    assert checkout.get("uses") == "actions/checkout@v7"
    checkout_inputs = _mapping(checkout.get("with"), "precommit-suite checkout inputs")
    assert checkout_inputs.get("fetch-depth") == 0


def test_hook_compares_against_origin_dev() -> None:
    assert _arg_value("--base-ref") == "origin/dev"


def test_reusable_job_is_required_and_strict_success() -> None:
    gate_module = importlib.import_module("scripts.ci.ci_summary_gate")
    gate_jobs = cast(tuple[str, ...], gate_module.GATE_JOBS)
    strict_success_jobs = cast(frozenset[str], gate_module.STRICT_SUCCESS_JOBS)

    assert GATE_JOB_NAME in gate_jobs
    assert GATE_JOB_NAME in strict_success_jobs
