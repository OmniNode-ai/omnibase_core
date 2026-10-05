# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for node_validation_report_write_effect (OMN-20565).

The EFFECT boundary that persists the canonical OMN-2362 report for a check
runtime's ``--report-json`` flag, so the check runtime packages stay free of
filesystem writes (the no-io-outside-effects gate).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

pytestmark = pytest.mark.unit


def _report() -> ModelValidationReport:
    return ModelValidationReport.from_findings(
        findings=(
            ModelValidationFindingEmbed(
                validator_id="arch-example",
                severity="FAIL",
                location="a.py:1",
                message="a.py:1: bad",
            ),
        ),
        request=ModelValidationRequestRef(profile="default"),
        validators_run=("arch-example",),
    )


def test_writes_report_that_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "out" / "report.json"
    report = _report()

    output = NodeValidationReportWriteEffect().handle(
        ModelValidationReportWriteInput(report_path=str(target), report=report)
    )

    assert output.report_path == str(target)
    assert ModelValidationReport.model_validate_json(target.read_text()) == report
    assert output.bytes_written == len(target.read_bytes())


def test_creates_missing_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "report.json"

    NodeValidationReportWriteEffect().handle(
        ModelValidationReportWriteInput(report_path=str(target), report=_report())
    )

    assert target.is_file()
