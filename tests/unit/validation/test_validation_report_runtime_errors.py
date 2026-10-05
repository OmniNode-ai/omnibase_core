# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``ModelValidationReport.from_runtime_errors`` (OMN-20565).

A check runtime that could not scan what it was asked to scan (a full-tree run
that gathered zero files, or a file that could not be read) must say so in the
canonical report as an ERROR finding, never report PASS.
"""

from __future__ import annotations

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

pytestmark = pytest.mark.unit


def test_from_runtime_errors_is_error_status_with_one_finding_per_message() -> None:
    report = ModelValidationReport.from_runtime_errors(
        validator_id="arch-example",
        messages=("zero files scanned under src", "a.py: read error: denied"),
    )

    assert report.overall_status == "ERROR"
    assert report.metrics.error_count == 2
    assert report.metrics.total == 2
    assert [f.message for f in report.findings] == [
        "zero files scanned under src",
        "a.py: read error: denied",
    ]
    assert {f.validator_id for f in report.findings} == {"arch-example"}
    assert report.provenance.validators_run == ("arch-example",)


def test_from_runtime_errors_with_no_messages_is_rejected() -> None:
    with pytest.raises(ModelOnexError, match="at least one message"):
        ModelValidationReport.from_runtime_errors(
            validator_id="arch-example", messages=()
        )
