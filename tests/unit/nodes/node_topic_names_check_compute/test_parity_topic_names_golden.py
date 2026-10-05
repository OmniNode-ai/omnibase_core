# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent core-script goldens; fixture sources are materialized verbatim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.topic_names_check.model_topic_names_check_input import (
    ModelTopicNamesCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_topic_names_check_compute.handler import (
    NodeTopicNamesCheckCompute,
)
from omnibase_core.nodes.node_topic_names_check_compute.runtime_topic_names_check import (
    main,
)

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]
FIXTURES = REPO / "tests/fixtures/validator_parity/topic_names"
CORPUS: dict[str, dict[str, str]] = json.loads((FIXTURES / "corpus.json").read_text())
GOLDEN = json.loads((FIXTURES / "golden.json").read_text())


def materialize(root: Path, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for path, source in CORPUS[name].items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    return root


def rows(report: ModelValidationReport) -> list[dict[str, str | int]]:
    result: list[dict[str, str | int]] = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        result.append({"path": path, "line": int(line), "message": finding.message})
    return result


def eligible(path: str) -> bool:
    file = Path(path)
    return "topic" in file.name and file.suffix in {".py", ".ts"}


@pytest.mark.parametrize("name", sorted(CORPUS))
def test_parity_golden_handler_and_runtime(
    name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = materialize(tmp_path / name, name)
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[
                ModelSourceFile(
                    path=path, source=(root / path).read_text(encoding="utf-8")
                )
                for path in sorted(CORPUS[name])
                if eligible(path)
            ]
        )
    )
    assert rows(report) == GOLDEN[name]["findings"]
    report_path = tmp_path / "report.json"
    assert (
        main([str(root), "--report-json", str(report_path)])
        == GOLDEN[name]["exit_code"]
    )
    assert capsys.readouterr().out == GOLDEN[name]["stdout"]
    saved = ModelValidationReport.model_validate_json(report_path.read_text())
    assert rows(saved) == GOLDEN[name]["findings"]


def test_parity_repo_source_tree_golden(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                "--root",
                str(REPO / "src"),
                "--report-json",
                str(report_path),
                "--verbose",
            ]
        )
        == GOLDEN["repo_src"]["exit_code"]
    )
    output = capsys.readouterr().out
    assert output.startswith("Scanned ")
    assert int(output.split()[1]) > 0
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert rows(report) == GOLDEN["repo_src"]["findings"]


def test_parity_corpus_covers_success_and_failure() -> None:
    assert any(case["exit_code"] == 0 for case in GOLDEN.values())
    assert any(case["exit_code"] == 1 for case in GOLDEN.values())
