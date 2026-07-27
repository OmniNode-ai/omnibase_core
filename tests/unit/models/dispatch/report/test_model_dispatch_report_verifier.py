# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDispatchReportVerifier (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` verifier-role suite. See
``test_model_dispatch_report_implementer.py`` for why validation goes
through ``model_validate_json``.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportVerifierVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_verifier import (
    ModelDispatchReportVerifier,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Re-ran the seeded RED/GREEN suite against the pushed commit and confirmed "
    "every violation fires through the real validator, not a mock."
)

_VERIFIED_SHA = "b" * 40


def _valid_payload() -> dict[str, object]:
    return {
        "role": "verifier",
        "pr_number": 4821,
        "verified_sha": _VERIFIED_SHA,
        "verdict": "confirmed",
        "evidence_paths": ["docs/evidence/SO-9999.md"],
        "summary": _SUBSTANTIVE_SUMMARY,
    }


def _validate(payload: dict[str, object]) -> ModelDispatchReportVerifier:
    return ModelDispatchReportVerifier.model_validate_json(json.dumps(payload))


def test_realistic_report_validates_green() -> None:
    """Mandatory GREEN: one realistic verifier report."""
    report = _validate(_valid_payload())
    assert report.role == "verifier"
    assert report.verdict == EnumDispatchReportVerifierVerdict.CONFIRMED
    assert report.evidence_paths == ["docs/evidence/SO-9999.md"]


def test_bare_ack_report_is_red() -> None:
    with pytest.raises(ValidationError, match="bare acknowledgement"):
        _validate({**_valid_payload(), "summary": "No further action taken."})


def test_literal_test_placeholder_fill_is_red() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate(
            {
                "role": "test",
                "pr_number": 1,
                "verified_sha": "test",
                "verdict": "test",
                "evidence_paths": ["test"],
                "summary": "test",
            }
        )
    errors = exc_info.value.errors()
    fields_with_errors = {".".join(str(part) for part in err["loc"]) for err in errors}
    assert "verdict" in fields_with_errors
    assert any("placeholder value 'test'" in err["msg"] for err in errors)


def test_evidence_paths_requires_at_least_one_entry() -> None:
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "evidence_paths": []})
