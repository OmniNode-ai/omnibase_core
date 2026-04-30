# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelCompletionVerifyResult."""

import pytest

from omnibase_core.models.validation.model_completion_verify_result import (
    ModelCompletionVerifyResult,
)


def test_result_required_fields() -> None:
    r = ModelCompletionVerifyResult(
        task_id="OMN-1",
        checked_identifiers=["foo", "bar"],
        found={"foo": "src/x.py"},
        missing=["bar"],
        skipped=False,
        skipped_reason=None,
    )
    assert r.missing == ["bar"]
    assert not r.skipped


def test_result_is_frozen() -> None:
    r = ModelCompletionVerifyResult(
        task_id="OMN-1",
        checked_identifiers=[],
        found={},
        missing=[],
        skipped=True,
        skipped_reason="no file targets",
    )
    with pytest.raises(Exception):
        r.task_id = "X"  # type: ignore[misc]


def test_result_all_found() -> None:
    r = ModelCompletionVerifyResult(
        task_id="OMN-2",
        checked_identifiers=["foo", "bar"],
        found={"foo": "src/x.py", "bar": "src/y.py"},
        missing=[],
        skipped=False,
        skipped_reason=None,
    )
    assert r.found == {"foo": "src/x.py", "bar": "src/y.py"}
    assert r.missing == []


def test_result_skipped_with_reason() -> None:
    r = ModelCompletionVerifyResult(
        task_id="OMN-RESEARCH",
        checked_identifiers=[],
        found={},
        missing=[],
        skipped=True,
        skipped_reason="no file targets resolved",
    )
    assert r.skipped
    assert r.skipped_reason == "no file targets resolved"


def test_result_skipped_reason_none_when_not_skipped() -> None:
    r = ModelCompletionVerifyResult(
        task_id="OMN-3",
        checked_identifiers=["baz"],
        found={},
        missing=["baz"],
        skipped=False,
        skipped_reason=None,
    )
    assert r.skipped_reason is None
