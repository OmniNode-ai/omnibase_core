# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20962: the boundary-validation job calls omnibase_core's own action.

OMN-20074 moved the validate-boundaries composite action out of the
change-control repository. The ``boundary-validation`` job in ci.yml keeps its
job id, name and check-run context and changes only its ``uses:`` line, to the
full commit sha of the merge that added the action (omnibase_core#1942).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"

JOB_ID = "boundary-validation"
CONTEXT = "Cross-repo boundary validation"
ACTION = "OmniNode-ai/omnibase_core/.github/actions/validate-boundaries"
# First eight hex digits of the omnibase_core#1942 merge; the rest must still be a full sha.
ACTION_SHA_PREFIX = "de3398d1"
_PINNED_USES = re.compile(rf"^{re.escape(ACTION)}@{ACTION_SHA_PREFIX}[0-9a-f]{{32}}$")
_RETIRED_ACTION = re.compile(
    r"onex_change_control/\.github/actions/validate-boundaries"
)


def _job() -> dict[str, Any]:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"][JOB_ID]


def _retired_references(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _RETIRED_ACTION.search(line)]


def test_boundary_validation_job_calls_the_core_action_at_the_merge_sha() -> None:
    uses = [s["uses"].split(" ")[0] for s in _job()["steps"] if "uses" in s]

    assert [u for u in uses if _PINNED_USES.fullmatch(u)] != []


def test_no_workflow_calls_the_retired_change_control_action() -> None:
    offenders = {
        path.name: _retired_references(path.read_text(encoding="utf-8"))
        for path in sorted((REPO_ROOT / ".github").rglob("*.yml"))
    }

    assert {name: refs for name, refs in offenders.items() if refs} == {}


def test_retired_action_reference_is_detected() -> None:
    old = (
        "      - uses: OmniNode-ai/onex_change_control/.github/actions/"
        "validate-boundaries@77f63a25b67db14dbca603ed8f841c3c5c4ee93e # dev"
    )

    assert _retired_references(old) == [old.strip()]


def test_inputs_job_name_and_required_context_are_unchanged() -> None:
    job = _job()
    step = next(s for s in job["steps"] if ACTION in s.get("uses", ""))

    assert job["name"] == CONTEXT
    assert step["with"] == {
        "checks": "boundary-parity",
        "warn-only": "false",
        "repos": "omniclaude,omnidash,omniintelligence,omnibase_infra,omnibase_core,omnimemory,omnimarket,onex_change_control",
    }
    entries = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    required = [e for e in _entries(entries) if e.get("name") == CONTEXT]
    assert [e["job_path"] for e in required] == [[JOB_ID]]


def _entries(doc: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(doc, dict):
        if "name" in doc and "job_path" in doc:
            found.append(doc)
        for value in doc.values():
            found.extend(_entries(value))
    elif isinstance(doc, list):
        for value in doc:
            found.extend(_entries(value))
    return found
