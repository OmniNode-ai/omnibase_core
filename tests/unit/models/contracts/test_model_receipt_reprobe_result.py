# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelReceiptReprobeResult / ModelReceiptReprobeReport (OMN-9789)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_receipt_reprobe_report import (
    ModelReceiptReprobeReport,
)
from omnibase_core.models.contracts.ticket.model_receipt_reprobe_result import (
    ModelReceiptReprobeResult,
)

pytestmark = pytest.mark.unit


def test_result_is_frozen() -> None:
    """ModelReceiptReprobeResult must be immutable once created."""
    result = ModelReceiptReprobeResult(
        receipt_path="/tmp/r.yaml",
        ticket_id="OMN-1",
        evidence_item_id="dod-001",
        check_type="command",
        status="PASS",
        detail="ok",
    )
    with pytest.raises(ValidationError):
        result.status = "FAIL"  # type: ignore[misc]


def test_result_rejects_extra_fields() -> None:
    """extra='forbid' guards against schema drift."""
    with pytest.raises(ValidationError):
        ModelReceiptReprobeResult(
            receipt_path="/tmp/r.yaml",
            ticket_id="OMN-1",
            evidence_item_id="dod-001",
            check_type="command",
            status="PASS",
            detail="ok",
            extra_field="nope",  # type: ignore[call-arg]
        )


def test_result_rejects_unknown_status() -> None:
    """Status must be one of the Literal options."""
    with pytest.raises(ValidationError):
        ModelReceiptReprobeResult(
            receipt_path="/tmp/r.yaml",
            ticket_id="OMN-1",
            evidence_item_id="dod-001",
            check_type="command",
            status="UNKNOWN",  # type: ignore[arg-type]
            detail="bad",
        )


def test_report_passed_is_true_when_empty() -> None:
    """Vacuous truth — no receipts = no failures."""
    report = ModelReceiptReprobeReport(receipts_dir="/tmp", results=[])
    assert report.passed is True
    assert report.failures == []


def test_report_passed_is_true_when_all_pass() -> None:
    report = ModelReceiptReprobeReport(
        receipts_dir="/tmp",
        results=[
            ModelReceiptReprobeResult(
                receipt_path="/tmp/a.yaml",
                ticket_id="OMN-1",
                evidence_item_id="dod-001",
                check_type="command",
                status="PASS",
                detail="ok",
            ),
            ModelReceiptReprobeResult(
                receipt_path="/tmp/b.yaml",
                ticket_id="OMN-2",
                evidence_item_id="dod-001",
                check_type="command",
                status="PASS",
                detail="ok",
            ),
        ],
    )
    assert report.passed is True
    assert report.failures == []


def test_report_passed_is_false_when_any_fail() -> None:
    fail = ModelReceiptReprobeResult(
        receipt_path="/tmp/b.yaml",
        ticket_id="OMN-2",
        evidence_item_id="dod-001",
        check_type="command",
        status="FAIL",
        detail="exit_code mismatch",
    )
    report = ModelReceiptReprobeReport(
        receipts_dir="/tmp",
        results=[
            ModelReceiptReprobeResult(
                receipt_path="/tmp/a.yaml",
                ticket_id="OMN-1",
                evidence_item_id="dod-001",
                check_type="command",
                status="PASS",
                detail="ok",
            ),
            fail,
        ],
    )
    assert report.passed is False
    assert report.failures == [fail]
