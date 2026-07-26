# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDispatchReportLander (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` lander-role suite. See
``test_model_dispatch_report_implementer.py`` for why validation goes
through ``model_validate_json``.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportLanderVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Squash-merged PR #4821 into main after CI went green on the second push; "
    "no conflicts, no CodeRabbit threads outstanding."
)

_MERGE_SHA = "c" * 40


def _valid_payload() -> dict[str, object]:
    return {
        "role": "lander",
        "pr_number": 4821,
        "merge_sha": _MERGE_SHA,
        "verdict": "merged",
        "summary": _SUBSTANTIVE_SUMMARY,
    }


def _validate(payload: dict[str, object]) -> ModelDispatchReportLander:
    return ModelDispatchReportLander.model_validate_json(json.dumps(payload))


def test_realistic_report_validates_green() -> None:
    """Mandatory GREEN: one realistic lander report."""
    report = _validate(_valid_payload())
    assert report.role == "lander"
    assert report.verdict == EnumDispatchReportLanderVerdict.MERGED


def test_bare_ack_report_is_red() -> None:
    with pytest.raises(ValidationError, match="bare acknowledgement"):
        _validate({**_valid_payload(), "summary": "Task complete."})


def test_literal_test_placeholder_fill_is_red() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate(
            {
                "role": "test",
                "pr_number": 1,
                "merge_sha": "test",
                "verdict": "test",
                "summary": "test",
            }
        )
    errors = exc_info.value.errors()
    fields_with_errors = {".".join(str(part) for part in err["loc"]) for err in errors}
    assert "verdict" in fields_with_errors
    assert any("placeholder value 'test'" in err["msg"] for err in errors)
