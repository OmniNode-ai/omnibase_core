# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Permanent old-runtime golden evidence for the hardcoded-topic node."""

from pathlib import Path

import pytest

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.handler import (
    NodeHardcodedTopicCheckCompute,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.runtime_hardcoded_topic_check import (
    _gather_paths,
    main,
)
from tests.unit.nodes.node_hardcoded_topic_check_compute.parity_helpers import (
    ROOT,
    materialize_parity_corpus,
    normalize_parity_report,
    normalize_parity_stdout,
    read_parity_golden,
)

pytestmark = pytest.mark.unit


def test_parity_hardcoded_topic_golden(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    materialize_parity_corpus(tmp_path)
    golden = read_parity_golden()
    files, errors = _gather_paths([tmp_path])
    assert not errors
    report = NodeHardcodedTopicCheckCompute().handle(
        ModelHardcodedTopicCheckInput(files=files)
    )
    assert normalize_parity_report(report, tmp_path) == golden["findings"]
    assert main([str(tmp_path)]) == golden["exit_code"]
    assert (
        normalize_parity_stdout(capsys.readouterr().out, tmp_path) == golden["findings"]
    )


def test_parity_hardcoded_topic_repo_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_root = ROOT / "src/omnibase_core"
    files, errors = _gather_paths([source_root])
    assert files and not errors
    report_path = tmp_path / "report.json"
    assert (
        main([str(source_root), "--report-only", "--report-json", str(report_path)])
        == 0
    )
    report = ModelValidationReport.model_validate_json(report_path.read_text())
    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert (
        len(normalize_parity_stdout(capsys.readouterr().out, source_root))
        == report.metrics.total
    )
