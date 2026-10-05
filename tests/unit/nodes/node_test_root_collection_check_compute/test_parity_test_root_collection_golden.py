# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent parity evidence against both read-only sibling validators."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.handler import (
    NodeTestRootCollectionCheckCompute,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.runtime_test_root_collection_check import (
    gather_request,
    main,
)
from tests.unit.nodes.node_test_root_collection_check_compute.parity_support import (
    CASES,
    GOLDEN,
    REPO_ROOT,
    materialize_parity_case,
    normalize_parity_message,
    parity_request,
)

pytestmark = pytest.mark.unit


def assert_parity_report(report: ModelValidationReport, name: str, root: Path) -> None:
    expected = GOLDEN["cases"][name]["omnibase_infra"]
    rows = [
        {
            "path": finding.location.rsplit(":", 1)[0],
            "line": int(finding.location.rsplit(":", 1)[1]),
            "message": normalize_parity_message(finding.message, root),
        }
        for finding in report.findings
        if finding.severity == "FAIL" and finding.location is not None
    ]
    assert rows == expected["findings"]
    errors = [
        normalize_parity_message(finding.message, root)
        for finding in report.findings
        if finding.severity == "ERROR"
    ]
    assert errors == (
        [expected["exception"]["message"]] if expected["exception"] else []
    )
    assert len(report.findings) == len(rows) + len(errors)
    assert report.overall_status == ("ERROR" if errors else "FAIL" if rows else "PASS")


@pytest.mark.parametrize("name", CASES)
def test_parity_golden_handler(name: str, tmp_path: Path) -> None:
    report = NodeTestRootCollectionCheckCompute().handle(parity_request(tmp_path, name))
    assert_parity_report(report, name, tmp_path)


@pytest.mark.parametrize("name", CASES)
def test_parity_golden_runtime(
    name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    materialize_parity_case(tmp_path, name)
    destination = tmp_path / "report.json"
    code = main(["--root", str(tmp_path), "--report-json", str(destination)])
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert_parity_report(report, name, tmp_path)
    expected = GOLDEN["cases"][name]["omnibase_infra"]
    assert code == expected["exit_code"]
    stdout = capsys.readouterr().out
    if expected["exception"] is None:
        assert normalize_parity_message(stdout, tmp_path) == expected["stdout"]
    else:
        assert expected["exception"]["message"] in normalize_parity_message(
            stdout, tmp_path
        )


def test_parity_core_tree(tmp_path: Path) -> None:
    request, scanned, errors = gather_request(REPO_ROOT)
    assert scanned > 0
    assert not errors
    report = NodeTestRootCollectionCheckCompute().handle(request)
    expected = GOLDEN["core_tree"]["omnibase_infra"]
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    assert (
        normalize_parity_message(report.findings[0].message, REPO_ROOT)
        == expected["exception"]["message"]
    )
    destination = tmp_path / "report.json"
    assert (
        main(["--root", str(REPO_ROOT), "--report-json", str(destination)])
        == expected["exit_code"]
    )
    written = ModelValidationReport.model_validate_json(destination.read_text())
    assert written.overall_status == report.overall_status
    assert [finding.message for finding in written.findings] == [
        finding.message for finding in report.findings
    ]
