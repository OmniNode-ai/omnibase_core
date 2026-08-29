# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Semantic severity for StatusGrid (OMN-16884, Phase C3).

The shipped config could not express the system-health board: a tile carried
``key``/``label``/``icon`` and nothing else, and the grid hard-coded four hex
colours in its own default. These tests pin the replacement and its two gates:

- **GC.4** — a ``critical`` tile renders a distinct **label and icon**, not only
  a colour.
- **GC.5** — no hex literal survives in any ``ModelWidgetConfig*`` default.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_status_secondary_kind import EnumStatusSecondaryKind
from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)
from omnibase_core.models.dashboard.model_severity_role import (
    DEFAULT_SEVERITY_ROLES,
    ModelSeverityRole,
)
from omnibase_core.models.dashboard.model_severity_verdict import ModelSeverityVerdict
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)
from omnibase_core.models.dashboard.model_status_secondary import ModelStatusSecondary
from omnibase_core.models.dashboard.model_widget_config_chart import (
    ModelWidgetConfigChart,
)
from omnibase_core.models.dashboard.model_widget_config_event_feed import (
    ModelWidgetConfigEventFeed,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_status_grid import (
    ModelWidgetConfigStatusGrid,
)
from omnibase_core.models.dashboard.model_widget_config_table import (
    ModelWidgetConfigTable,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

_HEX_LITERAL = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")

_WIDGET_CONFIG_MODELS: tuple[type[BaseModel], ...] = (
    ModelWidgetConfigChart,
    ModelWidgetConfigTable,
    ModelWidgetConfigMetricCard,
    ModelWidgetConfigStatusGrid,
    ModelWidgetConfigEventFeed,
)


def _verdict(
    severity: EnumStatusSeverity = EnumStatusSeverity.CRITICAL,
    status_value: str = "QUARANTINED",
) -> ModelSeverityVerdict:
    return ModelSeverityVerdict(
        severity=severity,
        status_value=status_value,
        policy_id="onex.policy.dlq_health",
        policy_version=ModelSemVer(major=1, minor=2, patch=0),
        policy_digest="sha256:" + "1" * 64,
    )


def _tile(
    key: str = "dlq",
    severity: EnumStatusSeverity = EnumStatusSeverity.CRITICAL,
    secondary: ModelStatusSecondary | None = None,
) -> ModelStatusItemConfig:
    return ModelStatusItemConfig(
        key=key,
        label=key.upper(),
        verdict=_verdict(severity),
        secondary=secondary,
    )


@pytest.mark.unit
class TestSeverityResolvesThroughTheTheme:
    """A severity names a theme token; it never carries a colour."""

    def test_every_default_role_points_at_a_real_theme_token(self) -> None:
        for role in DEFAULT_SEVERITY_ROLES:
            assert role.theme_color_token in ModelRendererThemeContract.model_fields

    def test_a_hex_value_is_rejected_where_a_token_name_belongs(self) -> None:
        with pytest.raises(ValidationError, match="theme_color_token"):
            ModelSeverityRole(
                severity=EnumStatusSeverity.CRITICAL,
                theme_color_token="#ef4444",
                label="Critical",
                icon="octagon-x",
            )

    def test_an_unknown_token_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="theme_color_token"):
            ModelSeverityRole(
                severity=EnumStatusSeverity.CRITICAL,
                theme_color_token="color_status_catastrophe",
                label="Critical",
                icon="octagon-x",
            )


@pytest.mark.unit
class TestGateGC4:
    """GC.4 — severity is never conveyed by colour alone."""

    def test_a_critical_tile_renders_a_distinct_label_and_icon(self) -> None:
        config = ModelWidgetConfigStatusGrid(items=(_tile(),))

        critical = config.role_for(EnumStatusSeverity.CRITICAL)
        others = [
            config.role_for(severity)
            for severity in EnumStatusSeverity
            if severity is not EnumStatusSeverity.CRITICAL
        ]

        assert critical.label
        assert critical.icon
        assert all(critical.label != role.label for role in others)
        assert all(critical.icon != role.icon for role in others)

    def test_the_board_is_legible_with_every_colour_removed(self) -> None:
        """Drop the token names entirely; the severities must still be distinct."""
        config = ModelWidgetConfigStatusGrid()

        monochrome = {(role.label, role.icon) for role in config.severity_roles}

        assert len(monochrome) == len(tuple(EnumStatusSeverity))

    def test_two_severities_sharing_an_icon_are_rejected(self) -> None:
        roles = tuple(
            role.model_copy(update={"icon": "same-icon"})
            for role in DEFAULT_SEVERITY_ROLES
        )

        with pytest.raises(ValidationError, match="distinct icon"):
            ModelWidgetConfigStatusGrid(severity_roles=roles)

    def test_two_severities_sharing_a_label_are_rejected(self) -> None:
        roles = tuple(
            role.model_copy(update={"label": "Same"}) for role in DEFAULT_SEVERITY_ROLES
        )

        with pytest.raises(ValidationError, match="distinct label"):
            ModelWidgetConfigStatusGrid(severity_roles=roles)

    def test_a_missing_severity_is_rejected(self) -> None:
        roles = tuple(
            role
            for role in DEFAULT_SEVERITY_ROLES
            if role.severity is not EnumStatusSeverity.UNKNOWN
        )

        with pytest.raises(ValidationError, match="missing"):
            ModelWidgetConfigStatusGrid(severity_roles=roles)


@pytest.mark.unit
class TestGateGC5:
    """GC.5 — no hex literal survives in any widget-config default."""

    def test_no_widget_config_default_contains_a_hex_literal(self) -> None:
        offenders: list[str] = []
        for model in _WIDGET_CONFIG_MODELS:
            for name, field in model.model_fields.items():
                default: Any = field.get_default(call_default_factory=True)
                if default is None:
                    continue
                rendered = json.dumps(default, default=str)
                if _HEX_LITERAL.search(rendered):
                    offenders.append(f"{model.__name__}.{name} = {rendered}")

        assert offenders == []

    def test_status_colors_is_gone_rather_than_deprecated(self) -> None:
        assert "status_colors" not in ModelWidgetConfigStatusGrid.model_fields

        with pytest.raises(ValidationError):
            ModelWidgetConfigStatusGrid(status_colors={"healthy": "#22c55e"})

    def test_a_status_grid_config_now_serialises_to_json(self) -> None:
        """The removed MappingProxyType default is what made this impossible.

        Before this change ``model_dump(mode="json")`` raised
        ``PydanticSerializationError: Unable to serialize unknown type:
        mappingproxy``, so a status-grid widget could not cross the wire the
        OMN-16883 envelope exists to cross.
        """
        payload = ModelWidgetConfigStatusGrid(items=(_tile(),)).model_dump(mode="json")

        assert payload["config_kind"] == "status_grid"
        assert payload["items"][0]["verdict"]["severity"] == "critical"


@pytest.mark.unit
class TestOrderingIsDeclared:
    """A grid sorts and summarises by declared rank, not by tile order."""

    def test_rank_orders_nominal_below_unknown_below_attention_below_critical(
        self,
    ) -> None:
        ranks = [severity.severity_rank for severity in EnumStatusSeverity]

        assert len(set(ranks)) == len(ranks)
        assert (
            EnumStatusSeverity.NOMINAL.severity_rank
            < EnumStatusSeverity.UNKNOWN.severity_rank
            < EnumStatusSeverity.ATTENTION.severity_rank
            < EnumStatusSeverity.CRITICAL.severity_rank
        )

    def test_items_sort_worst_first_then_by_key(self) -> None:
        config = ModelWidgetConfigStatusGrid(
            items=(
                _tile("zeta", EnumStatusSeverity.NOMINAL),
                _tile("beta", EnumStatusSeverity.CRITICAL),
                _tile("alpha", EnumStatusSeverity.CRITICAL),
                _tile("gamma", EnumStatusSeverity.UNKNOWN),
                _tile("delta", EnumStatusSeverity.ATTENTION),
            )
        )

        assert [item.key for item in config.items_worst_first()] == [
            "alpha",
            "beta",
            "delta",
            "gamma",
            "zeta",
        ]

    def test_summary_counts_every_severity_including_zero(self) -> None:
        config = ModelWidgetConfigStatusGrid(
            items=(
                _tile("a", EnumStatusSeverity.CRITICAL),
                _tile("b", EnumStatusSeverity.CRITICAL),
                _tile("c", EnumStatusSeverity.NOMINAL),
            )
        )

        counts = config.severity_counts()

        assert list(counts) == [
            EnumStatusSeverity.CRITICAL,
            EnumStatusSeverity.ATTENTION,
            EnumStatusSeverity.UNKNOWN,
            EnumStatusSeverity.NOMINAL,
        ]
        assert counts[EnumStatusSeverity.CRITICAL] == 2
        assert counts[EnumStatusSeverity.ATTENTION] == 0
        assert counts[EnumStatusSeverity.NOMINAL] == 1


@pytest.mark.unit
class TestVerdictsComeFromUpstream:
    """A tile's verdict is traceable to the policy that produced it."""

    def test_a_tile_without_a_verdict_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="verdict"):
            ModelStatusItemConfig(key="dlq", label="DLQ")

    def test_the_verdict_carries_the_policy_that_decided_it(self) -> None:
        tile = _tile()

        assert tile.verdict.policy_id == "onex.policy.dlq_health"
        assert tile.verdict.policy_version == ModelSemVer(major=1, minor=2, patch=0)
        assert tile.verdict.policy_digest.startswith("sha256:")

    def test_an_unhashed_policy_reference_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="policy_digest"):
            ModelSeverityVerdict(
                severity=EnumStatusSeverity.CRITICAL,
                status_value="QUARANTINED",
                policy_id="onex.policy.dlq_health",
                policy_version=ModelSemVer(major=1, minor=0, patch=0),
                policy_digest="v1.2.0",
            )

    def test_the_upstream_status_string_survives_the_mapping(self) -> None:
        """'STALLED' maps to critical without the tile forgetting it said STALLED."""
        tile = ModelStatusItemConfig(
            key="consumer_flow",
            label="Consumer flow",
            verdict=ModelSeverityVerdict(
                severity=EnumStatusSeverity.CRITICAL,
                status_value="STALLED",
                policy_id="onex.policy.consumer_flow",
                policy_version=ModelSemVer(major=1, minor=0, patch=0),
                policy_digest="sha256:" + "2" * 64,
            ),
        )

        assert tile.verdict.status_value == "STALLED"
        assert tile.verdict.severity is EnumStatusSeverity.CRITICAL


@pytest.mark.unit
class TestNumericSecondary:
    """A tile carries the number an operator actually reads."""

    def test_a_tile_carries_a_typed_numeric_secondary(self) -> None:
        tile = _tile(
            secondary=ModelStatusSecondary(
                kind=EnumStatusSecondaryKind.DEPTH,
                value=41902,
                label="DLQ depth",
            )
        )

        assert tile.secondary is not None
        assert tile.secondary.kind is EnumStatusSecondaryKind.DEPTH
        assert tile.secondary.value == 41902

    def test_a_rate_carries_its_unit(self) -> None:
        secondary = ModelStatusSecondary(
            kind=EnumStatusSecondaryKind.RATE,
            value=12.5,
            label="Arrivals",
            unit="msg/min",
        )

        assert secondary.unit == "msg/min"

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_values_are_rejected(self, value: float) -> None:
        with pytest.raises(ValidationError):
            ModelStatusSecondary(
                kind=EnumStatusSecondaryKind.RATE,
                value=value,
                label="Arrivals",
            )
