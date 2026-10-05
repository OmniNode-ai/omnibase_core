# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Permanent oracle snapshots, including the existing CI falsifier cases."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_ratchet_check_input import (
    ModelSkipCountRatchetCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.handler import (
    NodeSkipCountRatchetCheckCompute,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.runtime_skip_count_ratchet_check import (
    load_baseline,
    main,
    observe,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "tests/fixtures/validator_parity/skip_count_ratchet"
GOLDEN = json.loads((CORPUS / "golden.json").read_text())


@pytest.mark.parametrize("case", GOLDEN, ids=[c["label"] for c in GOLDEN])
def test_parity_skip_count_ratchet_golden(
    case: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(ROOT)
    args = case["args"]
    assert isinstance(args, list)
    report_path = tmp_path / "report.json"
    assert main([*args, "--report-json", str(report_path)]) == case["exit_code"]
    assert capsys.readouterr().out == case["stdout"]
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == (
        "PASS"
        if case["exit_code"] == 0
        else "FAIL"
        if case["exit_code"] == 1
        else "ERROR"
    )
    actual_runtime = [
        {
            "path": f.location.rsplit(":", 1)[0] if f.location else "",
            "line": int(f.location.rsplit(":", 1)[1]) if f.location else 0,
            "message": f.message,
        }
        for f in report.findings
    ]
    assert actual_runtime == case["findings"]
    if case["decision"] and case["exit_code"] != 2:
        paths = case["reports"]
        assert isinstance(paths, list)
        observation = observe([Path(p) for p in paths])
        baseline = load_baseline(Path(str(case["baseline"])), str(case["suite"]))
        direct = NodeSkipCountRatchetCheckCompute().handle(
            ModelSkipCountRatchetCheckInput(baseline=baseline, observation=observation)
        )
        expected = case["findings"]
        actual = [
            {
                "path": str(f.location).rsplit(":", 1)[0],
                "line": int(str(f.location).rsplit(":", 1)[1]),
                "message": f.message,
            }
            for f in direct.findings
        ]
        assert actual == expected
        assert [f.message for f in report.findings] == [
            f.message for f in direct.findings
        ]


@pytest.mark.parametrize(
    "suite", ["omnibase_core/tests-integration", "omnibase_core/test-parallel"]
)
def test_parity_skip_count_ratchet_repository_baseline(
    suite: str, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    artifact = CORPUS / "repository" / suite.rsplit("/", 1)[1] / "junit.xml"
    observation = observe([artifact])
    assert observation.files > 0
    assert observation.test_records > 0
    baseline = load_baseline(ROOT / "config/skip_count_baseline.yaml", suite)
    report = NodeSkipCountRatchetCheckCompute().handle(
        ModelSkipCountRatchetCheckInput(baseline=baseline, observation=observation)
    )
    assert report.overall_status == "PASS"
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--baseline",
                str(ROOT / "config/skip_count_baseline.yaml"),
                "--suite",
                suite,
                "--root",
                str(artifact.parent),
                "--report-json",
                str(destination),
            ]
        )
        == 0
    )
    assert "PASS" in capsys.readouterr().out
    assert main(["--selftest"]) == 0
    assert "2 shipped baseline suite(s) validated." in capsys.readouterr().out


def test_parity_skip_count_ratchet_required_empty_divergence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The task's mandatory zero-record rule strengthens the frozen oracle."""
    monkeypatch.chdir(ROOT)
    original = json.loads((CORPUS / "empty_golden.json").read_text())
    assert original["exit_code"] == 0
    assert "RATCHET CANDIDATE" in original["stdout"]
    destination = tmp_path / "report.json"
    assert main([*original["args"], "--report-json", str(destination)]) == 1
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert capsys.readouterr().out == (
        "::error::skip-count-ratchet input error (fail-closed): "
        "zero test records observed: a run that scans nothing is ERROR, never PASS\n"
    )


def test_parity_skip_count_ratchet_live_repository_inventory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Consume actual test records from repository source, rather than baseline IDs."""
    artifacts = tmp_path / "junit"
    artifacts.mkdir()
    artifact = artifacts / "junit.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:rerunfailures",
            "tests/unit/nodes/node_skip_count_ratchet_check_compute/test_node_skip_count_ratchet_check_compute.py",
            "-q",
            f"--junitxml={artifact}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    observation = observe([artifact])
    assert observation.test_records == observation.collected == 7
    assert observation.count == 0
    suite = "omnibase_core/test-parallel"
    baseline = load_baseline(ROOT / "config/skip_count_baseline.yaml", suite)
    direct = NodeSkipCountRatchetCheckCompute().handle(
        ModelSkipCountRatchetCheckInput(baseline=baseline, observation=observation)
    )
    assert direct.overall_status == "PASS"
    destination = tmp_path / "report.json"
    assert (
        main(
            [
                "--suite",
                suite,
                "--root",
                str(artifacts),
                "--report-json",
                str(destination),
            ]
        )
        == 0
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == direct.overall_status
    assert report.findings == direct.findings == ()
    golden = next(case for case in GOLDEN if case["label"] == "live-repository-unit")
    assert capsys.readouterr().out == golden["stdout"]
