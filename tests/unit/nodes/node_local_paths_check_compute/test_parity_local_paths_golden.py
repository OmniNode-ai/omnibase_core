# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Permanent parity against findings and console text captured from the old runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.local_paths_check.model_local_paths_check_input import (
    ModelLocalPathsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_local_paths_check_compute.handler import (
    NodeLocalPathsCheckCompute,
)
from omnibase_core.nodes.node_local_paths_check_compute.runtime_local_paths_check import (
    _gather_paths,
    main,
)
from tests.unit.nodes.node_local_paths_check_compute.parity_support import (
    FIXTURES,
    REPO,
    corpus,
    report_rows,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", sorted(corpus()))
@pytest.mark.parametrize("quiet", [False, True])
def test_parity_local_paths_golden(
    name: str, quiet: bool, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    expected = json.loads((FIXTURES / "golden.json").read_text())[name]
    path = tmp_path / f"{name}.txt"
    path.write_text(corpus()[name], encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    report = NodeLocalPathsCheckCompute().handle(
        ModelLocalPathsCheckInput(
            files=[ModelSourceFile(path=path.name, source=source)]
        )
    )
    assert report_rows(report) == [
        (row["path"], row["line"], row["rule"], row["message"])
        for row in expected["findings"]
    ]
    report_path = tmp_path / "report.json"
    assert (
        main([str(path), "--report-json", str(report_path), *(["-q"] if quiet else [])])
        == expected["exit_code"]
    )
    assert (
        capsys.readouterr().out.replace(str(path), path.name)
        == expected["output"]["quiet" if quiet else "verbose"]
    )
    persisted = ModelValidationReport.model_validate_json(report_path.read_text())
    assert [f.message.replace(str(path), path.name) for f in persisted.findings] == [
        row["message"] for row in expected["findings"]
    ]
    assert persisted.overall_status == report.overall_status


def test_parity_local_paths_full_tree_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = REPO / "src"
    files, errors = _gather_paths([root])
    assert files
    assert not errors
    report = NodeLocalPathsCheckCompute().handle(ModelLocalPathsCheckInput(files=files))
    assert report.overall_status == "PASS"
    destination = tmp_path / "report.json"
    code = main(["--root", str(root), "--quiet", "--report-json", str(destination)])
    assert code == (1 if report.findings else 0)
    actual = ModelValidationReport.model_validate_json(destination.read_text())
    assert report_rows(actual) == report_rows(report)
    capsys.readouterr()
