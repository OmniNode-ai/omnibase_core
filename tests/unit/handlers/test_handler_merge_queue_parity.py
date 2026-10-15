# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for HandlerMergeQueueParity (OMN-19998).

The positive fixtures are the two omnibase_infra jobs the merge queue ran and
pull request CI did not on 2026-10-15: ``runtime-boot-laptop-profile``, gated on
a paths job that answers ``changed=true`` for every event that is not a pull
request or a push, and ``runtime-boot-smoke``, whose ``if:`` names
``merge_group`` and not ``pull_request``.
"""

from __future__ import annotations

import textwrap

import pytest

from omnibase_core.enums.enum_merge_queue_parity_rule import EnumMergeQueueParityRule
from omnibase_core.handlers.handler_merge_queue_parity import (
    HandlerMergeQueueParity,
    merge_queue_only,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_baseline_entry import (
    ModelMergeQueueParityBaselineEntry,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_input import (
    ModelMergeQueueParityInput,
)

pytestmark = pytest.mark.unit

PATH = ".github/workflows/ci.yml"

TRIGGERS = """\
on:
  pull_request:
    branches: [dev]
  merge_group:
"""

LAPTOP = """\
jobs:
  laptop-profile-paths:
    runs-on: ubuntu-latest
    outputs:
      changed: ${{ steps.paths.outputs.changed }}
    steps:
      - id: paths
        env:
          EVENT_NAME: ${{ github.event_name }}
        run: |
          case "$EVENT_NAME" in
            pull_request) echo "changed=false" >> "$GITHUB_OUTPUT" ;;
            *) echo "changed=true" >> "$GITHUB_OUTPUT" ;;
          esac
  runtime-boot-laptop-profile:
    needs: [laptop-profile-paths]
    if: needs.laptop-profile-paths.outputs.changed == 'true'
    uses: ./.github/workflows/reusable-runtime-boot.yml
"""

SMOKE = """\
jobs:
  runtime-boot-smoke:
    needs: [tests-gate]
    if: >-
      (github.event_name == 'merge_group'
       || github.event_name == 'workflow_dispatch'
       || (github.event_name == 'push' && github.ref == 'refs/heads/main'))
      && needs.tests-gate.result == 'success'
    uses: ./.github/workflows/reusable-runtime-boot.yml
"""


def _run(
    *files: tuple[str, str],
    baseline: tuple[ModelMergeQueueParityBaselineEntry, ...] = (),
    stale: bool = False,
) -> tuple[str, list[tuple[str, str]]]:
    report = HandlerMergeQueueParity().handle(
        ModelMergeQueueParityInput(
            files=tuple(ModelSourceFile(path=p, source=s) for p, s in files),
            baseline=baseline,
            report_stale_baseline=stale,
        )
    )
    return report.overall_status, [(f.severity, f.message) for f in report.findings]


def test_a_job_gated_on_an_event_dependent_output_fails() -> None:
    status, findings = _run((PATH, TRIGGERS + LAPTOP))
    assert status == "FAIL"
    assert len(findings) == 1
    assert "runtime-boot-laptop-profile" in findings[0][1]
    assert EnumMergeQueueParityRule.EVENT_DEPENDENT_GATE.value in findings[0][1]


def test_a_job_whose_if_names_merge_group_and_not_pull_request_fails() -> None:
    status, findings = _run((PATH, TRIGGERS + SMOKE))
    assert status == "FAIL"
    assert "runtime-boot-smoke" in findings[0][1]
    assert EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF.value in findings[0][1]


def test_the_findings_carry_the_job_line() -> None:
    report = HandlerMergeQueueParity().handle(
        ModelMergeQueueParityInput(
            files=(ModelSourceFile(path=PATH, source=TRIGGERS + SMOKE),)
        )
    )
    assert report.findings[0].location == f"{PATH}:6"


@pytest.mark.parametrize(
    "condition",
    [
        "github.event_name != 'merge_group'",
        "github.event_name == 'pull_request' || github.event_name == 'merge_group'",
        "always() && needs.build.result == 'success'",
        "${{ github.event_name == 'pull_request' }}",
        "github.event_name == 'push'",
        "${{ !cancelled() }}",
        "always() && (github.event_name != 'pull_request' || "
        "github.base_ref != 'dev' || !github.event.pull_request.draft)",
    ],
)
def test_conditions_that_run_on_pull_requests_whenever_on_the_queue_pass(
    condition: str,
) -> None:
    body = (
        f"jobs:\n  j:\n    if: {condition}\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    status, findings = _run((PATH, TRIGGERS + body))
    assert (status, findings) == ("PASS", [])


@pytest.mark.parametrize(
    "condition",
    [
        "github.event_name == 'merge_group'",
        '${{ github.event_name == "merge_group" }}',
        "contains(github.event.pull_request.labels.*.name, 'x') "
        "&& github.event_name == 'merge_group'",
        "github.event_name != 'pull_request'",
        "!(github.event_name == 'pull_request')",
    ],
)
def test_merge_queue_only_conditions_are_detected(condition: str) -> None:
    assert merge_queue_only(condition)


def test_a_workflow_that_never_runs_on_the_queue_is_not_checked() -> None:
    text = "on:\n  push:\n    branches: [main]\n" + SMOKE
    assert _run((PATH, text)) == ("PASS", [])


def test_a_workflow_on_the_queue_but_not_on_pull_requests_fails() -> None:
    text = (
        "on:\n  merge_group:\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    status, findings = _run((PATH, text))
    assert status == "FAIL"
    assert EnumMergeQueueParityRule.NO_PULL_REQUEST_TRIGGER.value in findings[0][1]


def test_a_pull_request_path_filter_on_a_queue_workflow_fails() -> None:
    text = (
        "on:\n  pull_request:\n    paths: ['src/**']\n  merge_group:\n"
        "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    status, findings = _run((PATH, text))
    assert status == "FAIL"
    assert EnumMergeQueueParityRule.PULL_REQUEST_PATH_FILTER.value in findings[0][1]


def test_the_list_form_of_on_is_read() -> None:
    text = "on: [merge_group]\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
    status, _ = _run((PATH, text))
    assert status == "FAIL"


def test_a_gate_on_an_output_that_does_not_read_the_event_passes() -> None:
    body = textwrap.dedent(
        """\
        jobs:
          paths:
            runs-on: ubuntu-latest
            outputs:
              changed: ${{ steps.p.outputs.changed }}
            steps:
              - id: p
                run: echo "changed=true" >> "$GITHUB_OUTPUT"
          boot:
            needs: [paths]
            if: needs.paths.outputs.changed == 'true'
            runs-on: ubuntu-latest
            steps: []
        """
    )
    assert _run((PATH, TRIGGERS + body)) == ("PASS", [])


def test_a_baselined_violation_warns() -> None:
    entry = ModelMergeQueueParityBaselineEntry(
        path=PATH,
        job="runtime-boot-smoke",
        rule=EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF,
        ticket="OMN-19998",
    )
    status, findings = _run((PATH, TRIGGERS + SMOKE), baseline=(entry,))
    assert status == "WARN"
    assert findings[0][0] == "WARN"


def test_a_stale_baseline_entry_warns_on_a_full_tree_scan() -> None:
    entry = ModelMergeQueueParityBaselineEntry(
        path=PATH,
        job="gone",
        rule=EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF,
        ticket="OMN-19998",
    )
    status, findings = _run((PATH, TRIGGERS), baseline=(entry,), stale=True)
    assert status == "WARN"
    assert "stale baseline entry" in findings[0][1]


def test_an_unparseable_workflow_is_an_error() -> None:
    status, _ = _run((PATH, "on: [merge_group\n"))
    assert status == "ERROR"
