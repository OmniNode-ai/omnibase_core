# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23215: budget evidence says where a run's time limit came from.

A receipt names the ceiling's origin as a typed ``ceiling_source``: the packaged
contract or the site overlay. An overlay-sourced ceiling carries the overlay
reference it was read from; a packaged one carries none.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_delegation_ceiling_source import (
    EnumDelegationCeilingSource,
)
from omnibase_core.models.delegation.wire.model_delegation_budget_evidence import (
    ModelDelegationBudgetEvidence,
)


def _evidence(**overrides: object) -> ModelDelegationBudgetEvidence:
    fields: dict[str, object] = {
        "requested_timeout_seconds": None,
        "task_class_timeout_ceiling_seconds": 240,
        "execution_timeout_seconds": 240,
        "terminal_delivery_margin_seconds": 60,
    }
    fields.update(overrides)
    return ModelDelegationBudgetEvidence.model_validate(fields)


@pytest.mark.unit
class TestCeilingSource:
    def test_ceiling_source_accepts_packaged(self) -> None:
        evidence = _evidence(ceiling_source="packaged")
        assert evidence.ceiling_source is EnumDelegationCeilingSource.PACKAGED
        assert evidence.ceiling_overlay_ref is None

    def test_ceiling_source_accepts_overlay_with_its_reference(self) -> None:
        evidence = _evidence(
            ceiling_source="overlay", ceiling_overlay_ref="delegation_budgets"
        )
        assert evidence.ceiling_source is EnumDelegationCeilingSource.OVERLAY
        assert evidence.ceiling_overlay_ref == "delegation_budgets"

    def test_ceiling_source_refuses_any_other_value(self) -> None:
        for bad in ("site", "default", "PACKAGED ", "", None, 1):
            with pytest.raises(ValidationError):
                _evidence(ceiling_source=bad)

    def test_ceiling_source_values_are_exactly_packaged_and_overlay(self) -> None:
        assert {member.value for member in EnumDelegationCeilingSource} == {
            "packaged",
            "overlay",
        }

    def test_ceiling_source_defaults_to_packaged_for_legacy_evidence(self) -> None:
        evidence = _evidence()
        assert evidence.ceiling_source is EnumDelegationCeilingSource.PACKAGED

    def test_ceiling_source_overlay_requires_the_overlay_reference(self) -> None:
        with pytest.raises(ValidationError, match="ceiling_overlay_ref"):
            _evidence(ceiling_source="overlay")
        with pytest.raises(ValidationError, match="ceiling_overlay_ref"):
            _evidence(ceiling_source="overlay", ceiling_overlay_ref="")

    def test_ceiling_source_packaged_refuses_an_overlay_reference(self) -> None:
        with pytest.raises(ValidationError, match="ceiling_overlay_ref"):
            _evidence(
                ceiling_source="packaged", ceiling_overlay_ref="delegation_budgets"
            )

    def test_ceiling_source_round_trips_through_json(self) -> None:
        evidence = _evidence(
            ceiling_source="overlay", ceiling_overlay_ref="delegation_budgets"
        )
        restored = ModelDelegationBudgetEvidence.model_validate_json(
            evidence.model_dump_json()
        )
        assert restored == evidence
        assert restored.model_dump(mode="json")["ceiling_source"] == "overlay"
