# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import pytest
from pydantic import ValidationError

from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
    ModelTestSelection,
)


@pytest.mark.unit
def test_full_suite_selection_serializes_with_reason() -> None:
    selection = ModelTestSelection(
        selected_paths=["tests/"],
        split_count=40,
        is_full_suite=True,
        full_suite_reason=EnumFullSuiteReason.SHARED_MODULE,
        matrix=list(range(1, 41)),
    )
    payload = selection.model_dump(mode="json")
    assert payload == {
        "selected_paths": ["tests/"],
        "split_count": 40,
        "is_full_suite": True,
        "full_suite_reason": "shared_module",
        "matrix": list(range(1, 41)),
    }


@pytest.mark.unit
def test_smart_selection_disallows_full_suite_reason() -> None:
    with pytest.raises(ValidationError):
        ModelTestSelection(
            selected_paths=["tests/unit/nodes/"],
            split_count=2,
            is_full_suite=False,
            full_suite_reason=EnumFullSuiteReason.SHARED_MODULE,
            matrix=[1, 2],
        )


@pytest.mark.unit
def test_matrix_length_matches_split_count() -> None:
    with pytest.raises(ValidationError):
        ModelTestSelection(
            selected_paths=["tests/unit/nodes/"],
            split_count=3,
            is_full_suite=False,
            full_suite_reason=None,
            matrix=[1, 2],  # length mismatch
        )
