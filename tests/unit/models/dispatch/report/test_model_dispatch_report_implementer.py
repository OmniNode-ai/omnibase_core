# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDispatchReportImplementer (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` implementer-role suite,
driven directly against the real pydantic model (no anchor-context
resolution here -- that lives in
``tests/unit/validation/test_validator_dispatch_report_anchors.py``).

Validation goes through ``model_validate_json`` (not ``model_validate`` on a
plain dict), matching the documented pydantic v2 path for these
``ConfigDict(strict=True)`` models: strict *python*-mode validation requires
an actual ``Enum`` instance for enum fields, which a JSON payload naturally
deserializing to a plain string cannot satisfy; JSON-mode validation is the
correct path for external JSON input (e.g. an agent's report file) under
strict models.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportImplementerVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Implemented the golden-chain report contract module and CLI validator, "
    "added seeded RED/GREEN tests per role, and confirmed ruff/mypy/pytest "
    "all pass locally before opening the PR."
)

_HEAD_SHA = "a" * 40


def _valid_payload() -> dict[str, object]:
    return {
        "role": "implementer",
        "pr_number": 4821,
        "branch": "jonah/so-report-contracts-golden",
        "head_sha": _HEAD_SHA,
        "verdict": "implemented",
        "files_changed_paths": ["scripts/check_report_contract.py"],
        "summary": _SUBSTANTIVE_SUMMARY,
    }


def _validate(payload: dict[str, object]) -> ModelDispatchReportImplementer:
    return ModelDispatchReportImplementer.model_validate_json(json.dumps(payload))


def test_realistic_report_validates_green() -> None:
    """Mandatory GREEN: one realistic implementer report."""
    report = _validate(_valid_payload())
    assert report.role == "implementer"
    assert report.verdict == EnumDispatchReportImplementerVerdict.IMPLEMENTED
    assert report.pr_number == 4821
    assert report.files_changed_paths == ["scripts/check_report_contract.py"]


def test_model_is_frozen_and_extra_forbid() -> None:
    report = _validate(_valid_payload())
    with pytest.raises(ValidationError):
        report.pr_number = 1  # type: ignore[misc]
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "extra_field": "x"})


def test_bare_done_report_is_red() -> None:
    """Mandatory seeded RED: the exact 2026-07-25 failure mode."""
    with pytest.raises(ValidationError, match="bare acknowledgement"):
        _validate({**_valid_payload(), "summary": "Done."})


def test_literal_test_placeholder_fill_is_red() -> None:
    """Mandatory seeded RED: the worst class from the directive -- every
    string field filled with the literal word 'test'. This must fail on
    MULTIPLE independent grounds (role/verdict outside the closed set, SHA
    shape, placeholder summary), proving shape-only validation cannot let it
    through.
    """
    with pytest.raises(ValidationError) as exc_info:
        _validate(
            {
                "role": "test",
                "pr_number": 1,
                "branch": "test",
                "head_sha": "test",
                "verdict": "test",
                "files_changed_paths": ["test"],
                "summary": "test",
            }
        )
    errors = exc_info.value.errors()
    fields_with_errors = {".".join(str(part) for part in err["loc"]) for err in errors}
    assert "role" in fields_with_errors
    assert "verdict" in fields_with_errors
    assert "head_sha" in fields_with_errors
    assert any("placeholder value 'test'" in err["msg"] for err in errors)


def test_pr_number_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "pr_number": 0})
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "pr_number": -4})


def test_files_changed_paths_requires_at_least_one_entry() -> None:
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "files_changed_paths": []})


@pytest.mark.parametrize("bad_sha", ["", "xyz", "abc123"])
def test_head_sha_rejects_malformed_shapes(bad_sha: str) -> None:
    """SHAPE-only check here; resolution against a real git dir is the
    content-anchor validator's job (tested separately)."""
    with pytest.raises(ValidationError):
        _validate({**_valid_payload(), "head_sha": bad_sha})
