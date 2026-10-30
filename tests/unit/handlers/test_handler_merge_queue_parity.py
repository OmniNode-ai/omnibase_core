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

import ast
import importlib
import textwrap
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_merge_queue_parity_rule import EnumMergeQueueParityRule
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_baseline_entry import (
    ModelMergeQueueParityBaselineEntry,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_input import (
    ModelMergeQueueParityInput,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_rules import (
    ModelMergeQueueParityRules,
)
from omnibase_core.nodes.node_merge_queue_parity_check_effect.handler_merge_queue_parity import (
    HandlerMergeQueueParity,
    merge_queue_only,
)
from omnibase_core.validation.checker_workflow_selection import (
    load_parity_contract,
    load_parity_rules,
    parity_rules_from_contract,
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
            rules=load_parity_rules(),
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
            rules=load_parity_rules(),
            files=(ModelSourceFile(path=PATH, source=TRIGGERS + SMOKE),),
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
    assert merge_queue_only(condition, load_parity_rules())


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


NODE_DIR = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "nodes"
    / "node_merge_queue_parity_check_effect"
)
PARITY_ROW_IDS = (
    "trigger_events",
    "condition_expression",
    "finding_report",
    "no_pull_request_trigger",
    "pull_request_path_filter",
    "merge_queue_only_if",
    "event_dependent_gate",
)

DRAFT_GATE = (
    "jobs:\n  j:\n"
    "    if: github.event_name == 'merge_group' && github.event.pull_request.draft\n"
    "    runs-on: ubuntu-latest\n    steps: []\n"
)
NO_PR_TRIGGER = (
    "on:\n  merge_group:\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
)
PATH_FILTER = (
    "on:\n  pull_request:\n    paths: ['src/**']\n  merge_group:\n"
    "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
)
BRANCH_FILTER = TRIGGERS + "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n"
BASELINE_SMOKE = (
    ModelMergeQueueParityBaselineEntry(
        path=PATH,
        job="runtime-boot-smoke",
        rule=EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF,
        ticket="OMN-19998",
    ),
)
BASELINE_GONE = (
    ModelMergeQueueParityBaselineEntry(
        path=PATH,
        job="gone",
        rule=EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF,
        ticket="OMN-19998",
    ),
)


def _rules_with(
    row_id: str, key: str, value: str | int | list[str]
) -> ModelMergeQueueParityRules:
    contract = load_parity_contract()
    rows = [
        row.model_copy(update={"parameters": {**(row.parameters or {}), key: value}})
        if row.rule_id == row_id
        else row
        for row in contract.rules
    ]
    return parity_rules_from_contract(contract.model_copy(update={"rules": rows}))


def _report(
    rules: ModelMergeQueueParityRules,
    source: str,
    baseline: tuple[ModelMergeQueueParityBaselineEntry, ...] = (),
    stale: bool = False,
) -> list[tuple[str, str, str | None]]:
    report = HandlerMergeQueueParity().handle(
        ModelMergeQueueParityInput(
            rules=rules,
            files=(ModelSourceFile(path=PATH, source=source),),
            baseline=baseline,
            report_stale_baseline=stale,
        )
    )
    return [
        (report.overall_status, f.message, f.remediation) for f in report.findings
    ] or [(report.overall_status, "", None)]


# (row, key, mutated value, workflow source, baseline, stale)
MUTATIONS = [
    ("trigger_events", "queue_event", "merge_group_x", TRIGGERS + SMOKE, (), False),
    (
        "trigger_events",
        "pull_request_event",
        "merge_group",
        TRIGGERS + SMOKE,
        (),
        False,
    ),
    (
        "trigger_events",
        "pull_request_events",
        ["pull_request_target"],
        TRIGGERS + SMOKE,
        (),
        False,
    ),
    ("trigger_events", "path_filter_keys", ["branches"], BRANCH_FILTER, (), False),
    ("condition_expression", "event_atom_pattern", "^$", TRIGGERS + SMOKE, (), False),
    (
        "condition_expression",
        "draft_atom_pattern",
        "^$",
        TRIGGERS + DRAFT_GATE,
        (),
        False,
    ),
    (
        "condition_expression",
        "needs_output_pattern",
        "^$",
        TRIGGERS + LAPTOP,
        (),
        False,
    ),
    (
        "condition_expression",
        "event_name_pattern",
        "never_present_xyz",
        TRIGGERS + LAPTOP,
        (),
        False,
    ),
    ("condition_expression", "max_unknowns", 0, TRIGGERS + SMOKE, (), False),
    ("finding_report", "remediation", "Mutated fix.", TRIGGERS + SMOKE, (), False),
    (
        "finding_report",
        "finding_template",
        "MUT {rule} {detail}",
        TRIGGERS + SMOKE,
        (),
        False,
    ),
    (
        "finding_report",
        "baselined_template",
        "MUT {ticket} {message}",
        TRIGGERS + SMOKE,
        BASELINE_SMOKE,
        False,
    ),
    (
        "finding_report",
        "stale_template",
        "MUT {ticket} {path} {job} {rule}",
        TRIGGERS,
        BASELINE_GONE,
        True,
    ),
    (
        "no_pull_request_trigger",
        "message_template",
        "MUT no trigger",
        NO_PR_TRIGGER,
        (),
        False,
    ),
    (
        "pull_request_path_filter",
        "message_template",
        "MUT {event} filter",
        PATH_FILTER,
        (),
        False,
    ),
    (
        "merge_queue_only_if",
        "message_template",
        "MUT {job} {condition}",
        TRIGGERS + SMOKE,
        (),
        False,
    ),
    (
        "event_dependent_gate",
        "message_template",
        "MUT {job} {gate}",
        TRIGGERS + LAPTOP,
        (),
        False,
    ),
]


@pytest.mark.parametrize(
    ("row_id", "key", "value", "source", "baseline", "stale"),
    MUTATIONS,
    ids=[f"{m[0]}.{m[1]}" for m in MUTATIONS],
)
def test_mutating_a_rule_parameter_changes_the_verdict(
    row_id: str,
    key: str,
    value: str | int | list[str],
    source: str,
    baseline: tuple[ModelMergeQueueParityBaselineEntry, ...],
    stale: bool,
) -> None:
    before = _report(load_parity_rules(), source, baseline, stale)
    after = _report(_rules_with(row_id, key, value), source, baseline, stale)
    assert before != after


def test_every_parity_parameter_is_mutated_by_a_test() -> None:
    contract = load_parity_contract()
    declared = {
        (row.rule_id, key)
        for row in contract.rules
        if row.rule_id in PARITY_ROW_IDS
        for key in (row.parameters or {})
    }
    assert declared == {(m[0], m[1]) for m in MUTATIONS}
    assert {row.rule_id for row in contract.rules} == {"workflow_path", *PARITY_ROW_IDS}


@pytest.mark.parametrize(
    "module", ["handler_merge_queue_parity.py", "runtime_merge_queue_parity_check.py"]
)
def test_the_node_modules_hold_no_module_level_rule_table(module: str) -> None:
    tree = ast.parse((NODE_DIR / module).read_text("utf-8"))
    tables = []
    for node in tree.body:
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "cast"
            and len(value.args) == 2
            and isinstance(value.args[1], ast.Name)
            and isinstance(value.args[0], ast.Constant)
            and value.args[0].value == f"type[{value.args[1].id}]"
        ):
            continue  # Container service tokens are type references, not rule data.
        if isinstance(value, ast.Set | ast.Tuple | ast.Dict | ast.Call) or (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and len(value.value.split()) > 1
        ):
            tables.append(ast.unparse(node))
    assert tables == []


def test_the_node_contract_binds_the_handler() -> None:
    contract = yaml.safe_load((NODE_DIR / "contract.yaml").read_text("utf-8"))
    module_name, _, class_name = contract["handler_routing"][
        "default_handler"
    ].partition(":")
    module = importlib.import_module(
        f"omnibase_core.nodes.node_merge_queue_parity_check_effect.{module_name}"
    )
    assert getattr(module, class_name) is HandlerMergeQueueParity
    input_module, _, input_class = contract["input_model"].rpartition(".")
    assert getattr(importlib.import_module(input_module), input_class) is (
        ModelMergeQueueParityInput
    )
