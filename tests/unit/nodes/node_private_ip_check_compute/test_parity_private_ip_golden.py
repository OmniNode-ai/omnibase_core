# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent old-runtime golden parity and repository source scan."""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.private_ip_check.model_private_ip_check_input import (
    ModelPrivateIpCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_private_ip_check_compute.handler import (
    NodePrivateIpCheckCompute,
)
from omnibase_core.nodes.node_private_ip_check_compute.runtime_private_ip_check import (
    _gather_paths,
    main,
)

pytestmark = pytest.mark.unit


def test_parity_private_ip_golden(
    parity_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    golden_path = (
        Path(__file__).resolve().parents[3]
        / "fixtures/validator_parity/private_ip/golden.json"
    )
    golden = json.loads(golden_path.read_text())
    report_path = tmp_path / "report.json"
    code = main([str(parity_corpus), "--report-json", str(report_path)])
    stdout = capsys.readouterr().out.replace(str(parity_corpus) + "/", "")
    assert code == golden["exit_code"]
    assert stdout == golden["stdout"]
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    rows = []
    for finding in report.findings:
        assert finding.location is not None
        path, number = finding.location.rsplit(":", 1)
        rows.append(
            {
                "path": path.removeprefix(str(parity_corpus) + "/"),
                "line": int(number),
                "message": finding.message.replace(str(parity_corpus) + "/", ""),
            }
        )
    assert rows == golden["findings"]
    files, errors = _gather_paths([parity_corpus])
    assert not errors
    expected = NodePrivateIpCheckCompute().handle(ModelPrivateIpCheckInput(files=files))
    assert report.findings == expected.findings
    assert report.metrics == expected.metrics
    assert report.profile == expected.profile
    assert report.provenance.validators_run == expected.provenance.validators_run


def test_parity_private_ip_source_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = Path(__file__).resolve().parents[4] / "src"
    files, errors = _gather_paths([root])
    assert files
    assert not errors
    report_path = tmp_path / "tree.json"
    code = main(["--root", str(root), "--quiet", "--report-json", str(report_path)])
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert code == (0 if report.overall_status == "PASS" else 1)
    assert report.overall_status == "PASS"
    expected = NodePrivateIpCheckCompute().handle(ModelPrivateIpCheckInput(files=files))
    assert report.findings == expected.findings
    assert report.metrics == expected.metrics
    assert report.profile == expected.profile
    assert report.provenance.validators_run == expected.provenance.validators_run
    capsys.readouterr()


def test_parity_private_ip_hardcoded_node_comparison(parity_corpus: Path) -> None:
    from omnibase_core.models.nodes.no_hardcoded_ip_check.model_no_hardcoded_ip_check_input import (
        ModelNoHardcodedIpCheckInput,
    )
    from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
        ModelSourceFile,
    )
    from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.handler import (
        NodeNoHardcodedIpCheckCompute,
    )

    fixture_dir = (
        Path(__file__).resolve().parents[3] / "fixtures/validator_parity/private_ip"
    )
    corpus: dict[str, str] = json.loads((fixture_dir / "corpus.json").read_text())
    comparison = json.loads((fixture_dir / "comparison.json").read_text())
    differences = []
    for name in corpus:
        source = (parity_corpus / name).read_text()
        file = ModelSourceFile(path=name, source=source)
        private = NodePrivateIpCheckCompute().handle(
            ModelPrivateIpCheckInput(files=[file])
        )
        hardcoded = NodeNoHardcodedIpCheckCompute().handle(
            ModelNoHardcodedIpCheckInput(files=[file])
        )
        private_locations = {f.location for f in private.findings}
        hardcoded_locations = {f.location for f in hardcoded.findings}
        if private_locations != hardcoded_locations or len(private.findings) != len(
            hardcoded.findings
        ):
            differences.append(
                {
                    "input": name,
                    "private_count": len(private.findings),
                    "hardcoded_count": len(hardcoded.findings),
                    "private_only": sorted(private_locations - hardcoded_locations),
                    "hardcoded_only": sorted(hardcoded_locations - private_locations),
                }
            )
    assert differences == comparison["hardcoded_differences"]
