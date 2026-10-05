# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent parity evidence generated from both sibling scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_interpreter_check_input import (
    ModelPrecommitInterpreterCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.handler import (
    NodePrecommitInterpreterCheckCompute,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.runtime_precommit_interpreter_check import (
    main,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "tests/fixtures/validator_parity/precommit_interpreter"
CORPUS = json.loads((FIXTURES / "corpus.json").read_text())
GOLDEN = json.loads((FIXTURES / "golden.json").read_text())


def _parity_rows(report: ModelValidationReport) -> list[dict[str, str | int]]:
    rows = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        rows.append({"path": path, "line": int(line), "message": finding.message})
    return rows


@pytest.mark.parametrize("case", CORPUS, ids=[case["name"] for case in CORPUS])
def test_parity_precommit_interpreter_golden(
    case: dict[str, object], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    oracle = next(
        row["omnibase_infra"] for row in GOLDEN["cases"] if row["name"] == case["name"]
    )
    source = str(case["config"]).replace("${FIXTURE_ROOT}", str(tmp_path))
    scripts = case["scripts"]
    assert isinstance(scripts, dict)
    config = ModelSourceFile(path=".pre-commit-config.yaml", source=source)
    files = [ModelSourceFile(path=path, source=text) for path, text in scripts.items()]
    report = NodePrecommitInterpreterCheckCompute().handle(
        ModelPrecommitInterpreterCheckInput(
            config=config, scripts=files, repository_root=str(tmp_path)
        )
    )
    assert _parity_rows(report) == oracle["findings"]
    (tmp_path / config.path).write_text(source)
    for file in files:
        (tmp_path / file.path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / file.path).write_text(file.source)
    report_path = tmp_path / "report.json"
    assert (
        main(["--root", str(tmp_path), "--report-json", str(report_path)])
        == oracle["exit_code"]
    )
    captured = capsys.readouterr()
    assert captured.out == oracle["stdout"]
    assert captured.err == oracle["stderr"]
    saved = ModelValidationReport.model_validate_json(report_path.read_text())
    assert _parity_rows(saved) == oracle["findings"]
    assert saved.overall_status == report.overall_status


def test_parity_precommit_interpreter_core_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    oracle = GOLDEN["core_tree"]["omnibase_infra"]
    report_path = tmp_path / "report.json"
    assert (
        main(["--root", str(REPO_ROOT), "--report-json", str(report_path)])
        == oracle["exit_code"]
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert _parity_rows(report) == oracle["findings"]
    captured = capsys.readouterr()
    match = re.fullmatch(
        r"OK: (\d+) local pre-commit hooks and (\d+) referenced shell scripts "
        r"use a resolvable interpreter\n",
        captured.out,
    )
    assert match is not None
    assert int(match.group(1)) >= 10
    assert int(match.group(2)) > 0
    assert captured.err == oracle["stderr"]
    assert report.overall_status == "PASS"
