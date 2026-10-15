# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ci-inheritance handler (OMN-17427).

RULING 2026-10-14T20:01:09Z: all CI lives in omnibase_core and every
repository inherits from it. The handler refuses a change that ADDS a reusable
workflow or action call to an organization repository other than the host;
calls already present on the base are reported as WARN, never FAIL.
"""

from __future__ import annotations

import pytest

from omnibase_core.handlers.handler_ci_inheritance import (
    HandlerCiInheritance,
    extract_org_references,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
    ModelCiInheritanceCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

pytestmark = pytest.mark.unit

_CORE_CALL = """\
jobs:
  gate:
    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@abc123
"""

_OTHER_CALL = """\
jobs:
  hygiene:
    uses: OmniNode-ai/omniclaude/.github/workflows/hygiene-reusable.yml@abc123
"""

_OTHER_ACTION_STEP = """\
jobs:
  build:
    steps:
      - uses: actions/checkout@v7
      - name: parity
        uses: OmniNode-ai/omnibase_infra/.github/actions/wheel-content-parity@abc123
"""


def _request(
    base: dict[str, str], head: dict[str, str]
) -> ModelCiInheritanceCheckInput:
    return ModelCiInheritanceCheckInput(
        organization="OmniNode-ai",
        host_repository="omnibase_core",
        base_files=[ModelSourceFile(path=p, source=s) for p, s in base.items()],
        head_files=[ModelSourceFile(path=p, source=s) for p, s in head.items()],
    )


def test_added_non_host_reusable_workflow_fails() -> None:
    report = HandlerCiInheritance().handle(
        _request({"ci.yml": _CORE_CALL}, {"ci.yml": _CORE_CALL + _OTHER_CALL[5:]})
    )
    assert report.overall_status == "FAIL"
    fails = [f for f in report.findings if f.severity == "FAIL"]
    assert len(fails) == 1
    assert (
        "OmniNode-ai/omniclaude/.github/workflows/hygiene-reusable.yml"
        in fails[0].message
    )
    assert fails[0].location == "ci.yml:6"


def test_added_non_host_action_step_fails() -> None:
    report = HandlerCiInheritance().handle(
        _request({}, {"build.yml": _OTHER_ACTION_STEP})
    )
    assert report.overall_status == "FAIL"
    assert [f.location for f in report.findings] == ["build.yml:6"]


def test_added_host_call_passes() -> None:
    report = HandlerCiInheritance().handle(_request({}, {"gate.yml": _CORE_CALL}))
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_existing_non_host_call_is_warn_not_fail() -> None:
    report = HandlerCiInheritance().handle(
        _request({"a.yml": _OTHER_CALL}, {"a.yml": _OTHER_CALL})
    )
    assert report.overall_status == "WARN"
    assert [f.severity for f in report.findings] == ["WARN"]


def test_pin_bump_of_existing_call_is_not_new() -> None:
    bumped = _OTHER_CALL.replace("@abc123", "@def456")
    report = HandlerCiInheritance().handle(
        _request({"a.yml": _OTHER_CALL}, {"a.yml": bumped})
    )
    assert report.overall_status == "WARN"


def test_call_moved_between_files_is_not_new() -> None:
    report = HandlerCiInheritance().handle(
        _request({"a.yml": _OTHER_CALL}, {"b.yml": _OTHER_CALL})
    )
    assert report.overall_status == "WARN"


def test_removed_non_host_call_passes() -> None:
    report = HandlerCiInheritance().handle(
        _request({"a.yml": _OTHER_CALL}, {"a.yml": _CORE_CALL})
    )
    assert report.overall_status == "PASS"


def test_commented_and_local_uses_are_ignored() -> None:
    source = """\
# uses: OmniNode-ai/omniclaude/.github/workflows/x.yml@main
jobs:
  a:
    uses: ./.github/workflows/local.yml
    # uses: OmniNode-ai/omnimarket/.github/workflows/y.yml@main
"""
    assert extract_org_references(source, "OmniNode-ai") == []


def test_org_match_is_case_insensitive_and_quoted_values_parse() -> None:
    source = "    - uses: 'omninode-ai/omniclaude/.github/workflows/x.yml@main'\n"
    refs = extract_org_references(source, "OmniNode-ai")
    assert [(r.line, r.repository, r.target) for r in refs] == [
        (1, "omniclaude", "omninode-ai/omniclaude/.github/workflows/x.yml")
    ]


def test_host_match_is_case_insensitive() -> None:
    head = {"g.yml": _CORE_CALL.replace("omnibase_core", "OmniBase_Core")}
    report = HandlerCiInheritance().handle(_request({}, head))
    assert report.overall_status == "PASS"
