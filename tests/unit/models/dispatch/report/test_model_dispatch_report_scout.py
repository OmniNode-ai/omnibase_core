# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDispatchReportScout (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` scout-role suite. See
``test_model_dispatch_report_implementer.py`` for why validation goes
through ``model_validate_json``.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportScoutVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_scout import (
    ModelDispatchReportScout,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Located the existing structural-incentive model this ticket should mirror "
    "for style: one BaseModel per concept, frozen+extra=forbid+strict config."
)


def _valid_payload() -> dict[str, object]:
    return {
        "role": "scout",
        "verdict": "found",
        "findings_paths": ["src/steel_onslaught/contracts/incentive.py"],
        "summary": _SUBSTANTIVE_SUMMARY,
    }


def _validate(payload: dict[str, object]) -> ModelDispatchReportScout:
    return ModelDispatchReportScout.model_validate_json(json.dumps(payload))


def test_realistic_report_validates_green() -> None:
    """Mandatory GREEN: one realistic scout report."""
    report = _validate(_valid_payload())
    assert report.role == "scout"
    assert report.verdict == EnumDispatchReportScoutVerdict.FOUND
    assert report.pr_number is None


def test_scout_report_omits_pr_number_and_still_passes() -> None:
    """Scout is the one role with no PR requirement (investigation precedes
    any PR) -- a deliberate, documented per-role scope narrowing, not an
    accidental gap: pr_number stays optional only here.
    """
    payload = {
        "role": "scout",
        "verdict": "not_found",
        "findings_paths": ["src/steel_onslaught/contracts/incentive.py"],
        "summary": (
            "Searched the contracts/ tree for an existing report-contract model and found "
            "none; incentive.py is the closest style precedent to build the new one from."
        ),
    }
    report = _validate(payload)
    assert report.pr_number is None
    assert report.verdict == EnumDispatchReportScoutVerdict.NOT_FOUND


def test_bare_ack_report_is_red() -> None:
    with pytest.raises(ValidationError, match="bare acknowledgement"):
        _validate({**_valid_payload(), "summary": "Done."})


def test_literal_test_placeholder_fill_is_red() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate(
            {
                "role": "test",
                "verdict": "test",
                "findings_paths": ["test"],
                "summary": "test",
            }
        )
    errors = exc_info.value.errors()
    fields_with_errors = {".".join(str(part) for part in err["loc"]) for err in errors}
    assert "verdict" in fields_with_errors
    assert any("placeholder value 'test'" in err["msg"] for err in errors)


def test_findings_paths_requires_at_least_one_entry() -> None:
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "findings_paths": []})
