# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.plan import ModelDoDItem


@pytest.mark.unit
class TestModelDoDItem:
    def test_construct_minimal(self) -> None:
        item = ModelDoDItem(id="dod-1", description="Must render output correctly")
        assert item.id == "dod-1"
        assert item.description == "Must render output correctly"
        assert item.evidence_type is None
        assert item.satisfied is False

    def test_construct_full(self) -> None:
        item = ModelDoDItem(
            id="dod-2",
            description="Screenshot attached to PR",
            evidence_type="screenshot",
            satisfied=True,
        )
        assert item.evidence_type == "screenshot"
        assert item.satisfied is True

    def test_frozen(self) -> None:
        item = ModelDoDItem(id="dod-3", description="x")
        with pytest.raises(ValidationError):
            item.satisfied = True  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ModelDoDItem(id="dod-4", description="x", extra_field="nope")  # type: ignore[call-arg]

    def test_id_and_description_required_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            ModelDoDItem(id="", description="x")
        with pytest.raises(ValidationError):
            ModelDoDItem(id="dod-5", description="")

    def test_round_trip_json(self) -> None:
        original = ModelDoDItem(
            id="dod-6",
            description="Integration test green",
            evidence_type="integration_test",
            satisfied=True,
        )
        restored = ModelDoDItem.model_validate_json(original.model_dump_json())
        assert restored == original
