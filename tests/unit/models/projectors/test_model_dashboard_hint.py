# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelDashboardHint.

Covers:
1. Minimal construction — only widget_type required; defaults are correct.
2. Full construction — every field set, round-trips through model_dump.
3. Frozen invariant — mutation raises ValidationError.
4. extra='forbid' — unknown fields raise ValidationError.
5. priority bounds — 1 and 1000 valid; 0 and 1001 rejected.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dashboard_widget_type import EnumDashboardWidgetType
from omnibase_core.models.projectors.model_dashboard_hint import ModelDashboardHint


@pytest.mark.unit
def test_dashboard_hint_minimal_fields() -> None:
    """Only widget_type is required; all other fields default correctly."""
    hint = ModelDashboardHint(widget_type=EnumDashboardWidgetType.TILE)

    assert hint.widget_type == EnumDashboardWidgetType.TILE
    assert hint.label is None
    assert hint.group is None
    assert hint.priority == 100
    assert hint.time_series is False
    assert hint.unit is None


@pytest.mark.unit
def test_dashboard_hint_full_fields() -> None:
    """All fields may be set; model round-trips through model_dump."""
    hint = ModelDashboardHint(
        widget_type=EnumDashboardWidgetType.CHART,
        label="Active Nodes",
        group="platform",
        priority=10,
        time_series=True,
        unit="count",
    )

    assert hint.widget_type == EnumDashboardWidgetType.CHART
    assert hint.label == "Active Nodes"
    assert hint.group == "platform"
    assert hint.priority == 10
    assert hint.time_series is True
    assert hint.unit == "count"

    restored = ModelDashboardHint.model_validate(hint.model_dump())
    assert restored == hint


@pytest.mark.unit
def test_dashboard_hint_frozen() -> None:
    """Frozen model — mutation raises ValidationError."""
    hint = ModelDashboardHint(widget_type=EnumDashboardWidgetType.TABLE)

    with pytest.raises(ValidationError):
        hint.label = "new label"  # type: ignore[misc]


@pytest.mark.unit
def test_dashboard_hint_extra_forbidden() -> None:
    """extra='forbid' — unknown fields raise ValidationError."""
    with pytest.raises(ValidationError):
        ModelDashboardHint(
            widget_type=EnumDashboardWidgetType.TILE,
            unknown_field="value",  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_priority_bounds() -> None:
    """priority accepts 1..1000 inclusive; rejects 0 and 1001."""
    ModelDashboardHint(widget_type=EnumDashboardWidgetType.TILE, priority=1)
    ModelDashboardHint(widget_type=EnumDashboardWidgetType.TILE, priority=1000)

    with pytest.raises(ValidationError):
        ModelDashboardHint(widget_type=EnumDashboardWidgetType.TILE, priority=0)

    with pytest.raises(ValidationError):
        ModelDashboardHint(widget_type=EnumDashboardWidgetType.TILE, priority=1001)
