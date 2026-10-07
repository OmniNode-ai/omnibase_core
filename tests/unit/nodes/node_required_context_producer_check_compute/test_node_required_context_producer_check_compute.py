# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure handler producer resolution, branch selection, and fail-closed parsing."""

import pytest
import yaml

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_check_input import (
    ModelRequiredContextProducerCheckInput,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.handler import (
    NodeRequiredContextProducerCheckCompute,
)

from .conftest import MANIFEST, WORKFLOW, row

pytestmark = pytest.mark.unit


def check(head_rows, base_rows=None, base_ref=None, source="jobs:\n  produce: {}\n"):
    return NodeRequiredContextProducerCheckCompute().handle(
        ModelRequiredContextProducerCheckInput(
            head_manifest_text=yaml.safe_dump({"gates": head_rows}),
            base_manifest_text=None
            if base_rows is None
            else yaml.safe_dump({"gates": base_rows}),
            base_ref=base_ref,
            manifest_path=MANIFEST,
            head_workflows=(ModelSourceFile(path=WORKFLOW, source=source),),
        )
    )


@pytest.mark.parametrize(
    "producer",
    [
        row(job_path=["produce", "inner"]),
        row(
            workflow="external.yml",
            caller_workflow="producer.yml",
            caller_job="produce",
        ),
    ],
)
def test_caller_and_nested_job_resolution(producer):
    assert check([producer]).overall_status == "PASS"


@pytest.mark.parametrize(
    ("ref", "status"),
    [("origin/dev", "PASS"), ("origin/main", "FAIL"), ("main", "FAIL"), (None, "FAIL")],
)
def test_base_branch_selection(ref, status):
    report = check([], [row(branch="main")], ref)
    assert report.overall_status == status


def test_untagged_base_row_always_protected():
    assert check([], [row()], "origin/dev").overall_status == "FAIL"


@pytest.mark.parametrize("source", ["jobs: [\n", "jobs: []", "name: workflow"])
def test_bad_workflow_direct_handler(source):
    report = check([row()], source=source)
    assert report.overall_status == "ERROR"
    assert WORKFLOW in report.findings[0].message


def test_handler_is_deterministic():
    first = check([], [row()])
    second = check([], [row()])
    assert first.findings == second.findings
    assert first.provenance.validators_run == ("required-context-producer",)


@pytest.mark.parametrize(
    "invalid_row",
    [row(name=None), row(mode=None), row(workflow=None), row(job_path=[])],
)
def test_invalid_manifest_rows_fail_closed(invalid_row):
    report = check([invalid_row])
    assert report.overall_status == "ERROR"
    assert report.findings[0].rule_id == "unparseable_manifest"
    assert MANIFEST in report.findings[0].message


@pytest.mark.parametrize("text", ["gates: {}", "gates: !!set {}", "schema: 3"])
def test_manifest_requires_a_gates_list(text):
    report = NodeRequiredContextProducerCheckCompute().handle(
        ModelRequiredContextProducerCheckInput(
            head_manifest_text=text,
            base_manifest_text=None,
            base_ref=None,
            manifest_path=MANIFEST,
            head_workflows=(ModelSourceFile(path=WORKFLOW, source="jobs: {}"),),
        )
    )
    assert report.overall_status == "ERROR"
    assert report.findings[0].rule_id == "unparseable_manifest"
