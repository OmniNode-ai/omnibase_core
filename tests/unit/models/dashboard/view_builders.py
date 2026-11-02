# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixtures shared by the view-centric model tests (OMN-21997).

One builder per view kind for each of: config, row and section. A test that
parametrizes over ``VIEW_KINDS`` therefore covers every kind the suite knows,
and ``test_every_new_kind_has_a_builder`` fails when a kind is added without one.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_view_detail_entry import ModelViewDetailEntry
from omnibase_core.models.dashboard.model_view_document_digest import seal_view_document
from omnibase_core.models.dashboard.model_view_empty_state import ModelViewEmptyState
from omnibase_core.models.dashboard.model_view_row_drawer_detail import (
    ModelViewRowDrawerDetail,
)
from omnibase_core.models.dashboard.model_view_row_freshness import (
    ModelViewRowFreshness,
)
from omnibase_core.models.dashboard.model_view_row_id import ModelViewRowId
from omnibase_core.models.dashboard.model_view_row_line_card import (
    ModelViewRowLineCard,
)
from omnibase_core.models.dashboard.model_view_row_machine_bay import (
    ModelViewRowMachineBay,
)
from omnibase_core.models.dashboard.model_view_row_stage_progress import (
    ModelViewRowStageProgress,
)
from omnibase_core.models.dashboard.model_view_row_stop import ModelViewRowStop
from omnibase_core.models.dashboard.model_view_row_trend import ModelViewRowTrend
from omnibase_core.models.dashboard.model_view_section_drawer_detail import (
    ModelViewSectionDrawerDetail,
)
from omnibase_core.models.dashboard.model_view_section_freshness import (
    ModelViewSectionFreshness,
)
from omnibase_core.models.dashboard.model_view_section_line_card import (
    ModelViewSectionLineCard,
)
from omnibase_core.models.dashboard.model_view_section_machine_bay import (
    ModelViewSectionMachineBay,
)
from omnibase_core.models.dashboard.model_view_section_stage_progress import (
    ModelViewSectionStageProgress,
)
from omnibase_core.models.dashboard.model_view_section_stop import (
    ModelViewSectionStop,
)
from omnibase_core.models.dashboard.model_view_section_trend import (
    ModelViewSectionTrend,
)
from omnibase_core.models.dashboard.model_view_trend_point import ModelViewTrendPoint
from omnibase_core.models.dashboard.model_widget_config_drawer_detail import (
    ModelWidgetConfigDrawerDetail,
)
from omnibase_core.models.dashboard.model_widget_config_freshness import (
    ModelWidgetConfigFreshness,
)
from omnibase_core.models.dashboard.model_widget_config_line_card import (
    ModelWidgetConfigLineCard,
)
from omnibase_core.models.dashboard.model_widget_config_machine_bay import (
    ModelWidgetConfigMachineBay,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_stage_progress import (
    ModelWidgetConfigStageProgress,
)
from omnibase_core.models.dashboard.model_widget_config_stop import (
    ModelWidgetConfigStop,
)
from omnibase_core.models.dashboard.model_widget_config_trend import (
    ModelWidgetConfigTrend,
)
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_widget_envelope import seal_widget_envelope

if TYPE_CHECKING:
    from omnibase_core.models.dashboard.model_view_document import ModelViewDocument

VERSION = ModelSemVer(major=1, minor=0, patch=0)
VIEW_ID = "line-board"
MOMENT = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)

#: The seven kinds this ticket adds beside ``metric_card`` and ``chart``.
NEW_KINDS: tuple[str, ...] = (
    "line_card",
    "machine_bay",
    "stage_progress",
    "stop",
    "freshness",
    "trend",
    "drawer_detail",
)

CONFIG_BUILDERS: dict[str, Callable[[], Any]] = {
    "line_card": lambda: ModelWidgetConfigLineCard(show_detail=False),
    "machine_bay": lambda: ModelWidgetConfigMachineBay(columns=6),
    "stage_progress": lambda: ModelWidgetConfigStageProgress(show_percent=True),
    "stop": lambda: ModelWidgetConfigStop(show_duration=False),
    "freshness": lambda: ModelWidgetConfigFreshness(show_age=False),
    "trend": lambda: ModelWidgetConfigTrend(line_color="color_accent_primary"),
    "drawer_detail": lambda: ModelWidgetConfigDrawerDetail(open_by_default=True),
}


def section_id_for(kind: str) -> str:
    return f"{kind.replace('_', '-')}-section"


def row_id(kind: str, key: str = "a1") -> ModelViewRowId:
    return ModelViewRowId(
        view_id=VIEW_ID, section_id=section_id_for(kind), key_values=(key,)
    )


ROW_BUILDERS: dict[str, Callable[[ModelViewRowId], Any]] = {
    "line_card": lambda rid: ModelViewRowLineCard(
        row_id=rid,
        label="Line 1",
        severity=EnumStatusSeverity.ATTENTION,
        status_text="Slow",
    ),
    "machine_bay": lambda rid: ModelViewRowMachineBay(
        row_id=rid,
        bay_label="Bay 3",
        severity=EnumStatusSeverity.NOMINAL,
        state_text="Running",
    ),
    "stage_progress": lambda rid: ModelViewRowStageProgress(
        row_id=rid,
        label="Order 7",
        stage_label="Weld",
        stage_index=2,
        stage_count=5,
    ),
    "stop": lambda rid: ModelViewRowStop(
        row_id=rid,
        label="Press 2",
        reason_text="Tool change",
        severity=EnumStatusSeverity.CRITICAL,
        started_at=MOMENT,
    ),
    "freshness": lambda rid: ModelViewRowFreshness(
        row_id=rid,
        label="Orders feed",
        observed_at=MOMENT,
        max_age_seconds=300,
        severity=EnumStatusSeverity.NOMINAL,
    ),
    "trend": lambda rid: ModelViewRowTrend(
        row_id=rid,
        label="Throughput",
        points=(
            ModelViewTrendPoint(at=MOMENT, value=1.5),
            ModelViewTrendPoint(at=MOMENT.replace(hour=11), value=2.25),
        ),
    ),
    "drawer_detail": lambda rid: ModelViewRowDrawerDetail(
        row_id=rid,
        title="Press 2 detail",
        entries=(ModelViewDetailEntry(label="Operator", value="Night shift"),),
    ),
}

SECTION_CLASSES: dict[str, type] = {
    "line_card": ModelViewSectionLineCard,
    "machine_bay": ModelViewSectionMachineBay,
    "stage_progress": ModelViewSectionStageProgress,
    "stop": ModelViewSectionStop,
    "freshness": ModelViewSectionFreshness,
    "trend": ModelViewSectionTrend,
    "drawer_detail": ModelViewSectionDrawerDetail,
}


def envelope(kind: str, config: Any | None = None) -> ModelWidgetEnvelope:
    """A sealed envelope for ``kind``; ``config`` overrides the default config."""
    return seal_widget_envelope(
        widget_id=f"onex.widget.view_{kind}",
        widget_version=VERSION,
        component=ModelComponentContract(
            component_id=f"onex.component.view_{kind}",
            component_kind=EnumWidgetType(kind),
            title=f"View {kind}",
            contract_version=VERSION,
        ),
        config=config if config is not None else CONFIG_BUILDERS[kind](),
        provenance=ModelWidgetProvenance(
            pack_namespace="onex.packs.platform",
            pack_name="views",
            pack_version=VERSION,
            source_revision="0" * 40,
        ),
    )


def section(kind: str, *, rows: int = 1, empty: bool = False) -> Any:
    """A section of ``kind`` with ``rows`` rows, or a typed empty state."""
    if empty:
        return SECTION_CLASSES[kind](
            section_id=section_id_for(kind),
            envelope=envelope(kind),
            empty_state=ModelViewEmptyState(reason=EnumEmptyStateReason.NO_DATA),
        )
    return SECTION_CLASSES[kind](
        section_id=section_id_for(kind),
        envelope=envelope(kind),
        rows=tuple(
            ROW_BUILDERS[kind](row_id(kind, f"k{index}")) for index in range(rows)
        ),
    )


def document(kinds: tuple[str, ...] = NEW_KINDS) -> ModelViewDocument:
    return seal_view_document(
        view_id=VIEW_ID,
        contract_version=VERSION,
        generated_at=MOMENT,
        sections=tuple(section(kind) for kind in kinds),
    )


def metric_card_envelope() -> ModelWidgetEnvelope:
    return seal_widget_envelope(
        widget_id="onex.widget.view_metric_card",
        widget_version=VERSION,
        component=ModelComponentContract(
            component_id="onex.component.view_metric_card",
            component_kind=EnumWidgetType.METRIC_CARD,
            title="Metric",
            contract_version=VERSION,
        ),
        config=ModelWidgetConfigMetricCard(metric_key="oee", label="OEE"),
        provenance=ModelWidgetProvenance(
            pack_namespace="onex.packs.platform",
            pack_name="views",
            pack_version=VERSION,
            source_revision="0" * 40,
        ),
    )
