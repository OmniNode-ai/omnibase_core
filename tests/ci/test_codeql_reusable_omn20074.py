# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: CodeQL reusable workflow moved from onex_change_control into omnibase_core.

A caller that repoints to this file keeps the required context
``CodeQL / CodeQL Analysis (python)`` byte-identical, so the job name, the
inputs and the permissions must equal the moved file's.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
REUSABLE_PATH = WORKFLOWS_DIR / "codeql-reusable.yml"

# Verbatim from the moved file, so a drift in either direction fails here.
_JOB_NAME_EXPRESSION = "CodeQL Analysis (${{ inputs.language }})"
_CALLER_JOB_NAME = "CodeQL"
_REQUIRED_CONTEXT = "CodeQL / CodeQL Analysis (python)"
_FORBIDDEN_REFERENCE = "onex_change_control"
_FULL_SHA_USES = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _load() -> dict[str, Any]:
    data = yaml.safe_load(REUSABLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers(data: dict[str, Any]) -> dict[str, Any]:
    # PyYAML 1.1 resolves the bare `on:` key to the boolean True.
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict), "workflow must declare a mapping on: block"
    return triggers


def _references_occ(text: str) -> bool:
    return _FORBIDDEN_REFERENCE in text


def test_reusable_is_workflow_call_only() -> None:
    assert set(_triggers(_load())) == {"workflow_call"}


def test_inputs_match_the_moved_file() -> None:
    inputs = _triggers(_load())["workflow_call"]["inputs"]
    assert set(inputs) == {"language", "query_suite"}
    assert inputs["language"]["type"] == "string"
    assert inputs["language"]["required"] is False
    assert inputs["language"]["default"] == "python"
    assert inputs["query_suite"]["type"] == "string"
    assert inputs["query_suite"]["required"] is False
    assert inputs["query_suite"]["default"] == "security-and-quality"


def test_job_name_and_permissions_match_the_moved_file() -> None:
    jobs = _load()["jobs"]
    assert set(jobs) == {"analyze"}
    job = jobs["analyze"]
    assert job["name"] == _JOB_NAME_EXPRESSION
    assert job["permissions"] == {
        "actions": "read",
        "contents": "read",
        "security-events": "write",
    }


def test_required_context_is_byte_identical_for_a_caller() -> None:
    job_name = _load()["jobs"]["analyze"]["name"]
    resolved = job_name.replace("${{ inputs.language }}", "python")
    assert resolved == "CodeQL Analysis (python)"
    caller = yaml.safe_load(
        (WORKFLOWS_DIR / "security-scan.yml").read_text(encoding="utf-8")
    )
    assert caller["jobs"]["codeql"]["name"] == _CALLER_JOB_NAME
    assert f"{_CALLER_JOB_NAME} / {resolved}" == _REQUIRED_CONTEXT


def test_no_step_references_onex_change_control() -> None:
    data = _load()
    for step in data["jobs"]["analyze"]["steps"]:
        assert not _references_occ(yaml.safe_dump(step)), step
    assert not _references_occ(REUSABLE_PATH.read_text(encoding="utf-8"))


def test_reference_check_has_a_positive_control() -> None:
    assert _references_occ(
        "uses: OmniNode-ai/onex_change_control/.github/workflows/codeql-reusable.yml@main"
    )
    assert not _references_occ("uses: github/codeql-action/init@" + "0" * 40)


def test_third_party_actions_are_pinned_by_full_sha() -> None:
    uses = [s["uses"] for s in _load()["jobs"]["analyze"]["steps"] if "uses" in s]
    assert [u.split("@")[0] for u in uses] == [
        "actions/checkout",
        "github/codeql-action/init",
        "github/codeql-action/autobuild",
        "github/codeql-action/analyze",
    ]
    for ref in uses:
        assert _FULL_SHA_USES.match(ref), f"{ref} must be pinned by a full sha"
