# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Permanent artifact parity against recorded sibling script executions."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_integration_skips_check_compute.handler import (
    NodeIntegrationSkipsCheckCompute,
)
from omnibase_core.nodes.node_integration_skips_check_compute.runtime_integration_skips_check import (
    config_from_source,
    input_from_sources,
    main,
)

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "tests/fixtures/validator_parity/integration_skips"
GOLDEN = json.loads((CORPUS / "golden.json").read_text())


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda case: case["name"])
def test_parity_golden_runtime_and_handler(
    case,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    working = CORPUS
    if "unreadable.xml" in case["args"]:
        working = tmp_path
        shutil.copy(CORPUS / "config.yaml", working / "config.yaml")
        shutil.copy(CORPUS / "unreadable.xml", working / "unreadable.xml")
        (working / "unreadable.xml").chmod(0)
    monkeypatch.chdir(working)
    oracle = case["oracles"]["omnibase_infra"]
    report_path = tmp_path / "report.json"
    assert (
        main([*case["args"], "--report-json", str(report_path)]) == oracle["exit_code"]
    )
    assert capsys.readouterr().out == oracle["stdout"]
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    rows = []
    for finding in report.findings:
        if finding.location is None:
            path, line = None, None
        else:
            path, raw_line = finding.location.rsplit(":", 1)
            line = int(raw_line)
        rows.append({"path": path, "line": line, "message": finding.message})
    assert rows == oracle["findings"]
    if "--selftest" in case["args"]:
        assert report.overall_status == ("PASS" if oracle["exit_code"] == 0 else "FAIL")
        return
    if oracle["exit_code"] == 2 or "unreadable.xml" in case["args"]:
        assert report.overall_status == "ERROR"
        return
    args = case["args"]
    config = config_from_source((CORPUS / args[args.index("--config") + 1]).read_text())
    start = args.index("--junit") + 1
    names = []
    for name in args[start:]:
        if name.startswith("--"):
            break
        names.append(name)
    request = input_from_sources(
        [
            ModelSourceFile(path=name, source=(CORPUS / name).read_text())
            for name in names
        ],
        config,
        strict="--strict" in args,
    )
    direct = NodeIntegrationSkipsCheckCompute().handle(request)
    assert direct.findings == report.findings
    assert direct.overall_status == report.overall_status


def test_parity_core_tree_no_artifact_matches_recorded_script(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    oracle = GOLDEN["core_tree"]["omnibase_infra"]
    assert oracle["junit_files"] == 0
    assert not list((REPO / "src").rglob("*.xml"))
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                "--root",
                str(REPO / "src"),
                "--config",
                str(CORPUS / "config.yaml"),
                "--report-json",
                str(report_path),
            ]
        )
        == oracle["exit_code"]
    )
    assert capsys.readouterr().out == oracle["stdout"]
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "ERROR"
    assert [f.message for f in report.findings] == [
        "--junit is required (or use --selftest)"
    ]


def test_parity_sibling_gate_rules_differ_only_in_message_wording() -> None:
    for case in GOLDEN["cases"]:
        if case["name"] in {"selftest_infra_specific", "selftest_market_specific"}:
            continue
        infra = case["oracles"]["omnibase_infra"]
        market = case["oracles"]["omnimarket"]
        assert infra["exit_code"] == market["exit_code"]
        assert (
            market["stdout"].replace(
                "This job provisions", "The merge-gating job provisions"
            )
            == infra["stdout"]
        )
        normalized = [
            {
                **row,
                "message": row["message"].replace(
                    "This job provisions", "The merge-gating job provisions"
                ),
            }
            for row in market["findings"]
        ]
        assert normalized == infra["findings"]


@pytest.mark.parametrize(
    ("name", "infra_code", "market_code"),
    [("selftest_infra_specific", 0, 1), ("selftest_market_specific", 1, 0)],
)
def test_parity_sibling_selftest_fixture_difference_is_recorded(
    name: str, infra_code: int, market_code: int
) -> None:
    case = next(case for case in GOLDEN["cases"] if case["name"] == name)
    assert case["oracles"]["omnibase_infra"]["exit_code"] == infra_code
    assert case["oracles"]["omnimarket"]["exit_code"] == market_code
