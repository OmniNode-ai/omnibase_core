# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Widget type enumeration for dashboard widgets.

This module defines the available widget types for dashboard configuration.
Each widget type corresponds to a specific visualization style and has its
own configuration model in the dashboard models package.

Example:
    Check widget type properties::

        from omnibase_core.enums import EnumWidgetType

        widget_type = EnumWidgetType.CHART
        if widget_type.is_data_bound:
            print("This widget needs a data source")
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ("EnumWidgetType",)


_ROW_DRIVEN_VIEW_KIND_VALUES: frozenset[str] = frozenset(
    {
        "line_card",
        "machine_bay",
        "stage_progress",
        "stop",
        "freshness",
        "trend",
        "drawer_detail",
    }
)


@unique
class EnumWidgetType(UtilStrValueHelper, str, Enum):
    """Dashboard widget type enumeration.

    Defines the types of widgets available for dashboard configuration.
    Each type has specific configuration requirements and rendering behavior.
    Widget types are categorized as either data-bound (requiring continuous
    data updates) or aggregation-based (displaying point-in-time metrics).

    Attributes:
        CHART: Line, bar, area, pie, or scatter chart visualization.
            Config: :class:`~omnibase_core.models.dashboard.ModelWidgetConfigChart`
        TABLE: Paginated, sortable tabular data display.
            Config: :class:`~omnibase_core.models.dashboard.ModelWidgetConfigTable`
        METRIC_CARD: Single KPI display with optional trend and thresholds.
            Config: :class:`~omnibase_core.models.dashboard.ModelWidgetConfigMetricCard`
        STATUS_GRID: Grid of status indicators for system health monitoring.
            Config: :class:`~omnibase_core.models.dashboard.ModelWidgetConfigStatusGrid`
        EVENT_FEED: Real-time event stream with filtering capabilities.
            Config: :class:`~omnibase_core.models.dashboard.ModelWidgetConfigEventFeed`
        LINE_CARD: One production line's status as a card (view-centric kind).
        MACHINE_BAY: One machine bay and its current state (view-centric kind).
        STAGE_PROGRESS: Position of an item within an ordered set of stages.
        STOP: A stoppage, its reason and when it began (view-centric kind).
        FRESHNESS: How old a feed's last observation is against its allowance.
        TREND: A series of timestamped values for one measure.
        DRAWER_DETAIL: Labelled detail entries shown in an expandable drawer.

    The seven view-centric kinds (``LINE_CARD`` through ``DRAWER_DETAIL``) are
    row-driven: each has a config in the ``ModelWidgetConfig`` union and a row
    model under ``models/dashboard/model_view_row_*``. Together with
    ``METRIC_CARD`` they are the eight view kinds (:attr:`is_view_kind`).

    Example:
        Use in widget definition::

            from omnibase_core.enums import EnumWidgetType

            # Check if widget needs real-time data binding
            if EnumWidgetType.TABLE.is_data_bound:
                setup_data_subscription()
    """

    CHART = "chart"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    STATUS_GRID = "status_grid"
    EVENT_FEED = "event_feed"
    LINE_CARD = "line_card"
    MACHINE_BAY = "machine_bay"
    STAGE_PROGRESS = "stage_progress"
    STOP = "stop"
    FRESHNESS = "freshness"
    TREND = "trend"
    DRAWER_DETAIL = "drawer_detail"

    @property
    def is_data_bound(self) -> bool:
        """Check if widget type requires external data binding.

        Data-bound widgets (CHART, TABLE, EVENT_FEED and the seven row-driven
        view kinds) display real-time or historical data from external
        sources. They need continuous data updates and typically subscribe to a
        data source for real-time updates.

        Note:
            Mutually exclusive with :attr:`is_aggregation` - a widget type is
            either data-bound OR aggregation, never both. All defined widget
            types fall into exactly one of these two categories.

        Returns:
            True if the widget type requires data binding (CHART, TABLE,
            EVENT_FEED and the row-driven view kinds), False otherwise
            (METRIC_CARD, STATUS_GRID).
        """
        return (
            self
            in {
                EnumWidgetType.CHART,
                EnumWidgetType.TABLE,
                EnumWidgetType.EVENT_FEED,
            }
            or self.value in _ROW_DRIVEN_VIEW_KIND_VALUES
        )

    @property
    def is_view_kind(self) -> bool:
        """Check if this is one of the eight view kinds.

        The view kinds are what a view contract may declare for a section:
        ``METRIC_CARD`` plus the seven row-driven kinds. ``CHART``, ``TABLE``,
        ``STATUS_GRID`` and ``EVENT_FEED`` are dashboard widgets, not view kinds.

        Returns:
            True for METRIC_CARD and the seven row-driven view kinds.
        """
        return self is EnumWidgetType.METRIC_CARD or (
            self.value in _ROW_DRIVEN_VIEW_KIND_VALUES
        )

    @property
    def is_aggregation(self) -> bool:
        """Check if widget type displays aggregated/computed values.

        Aggregation widgets (METRIC_CARD, STATUS_GRID) show pre-computed
        summary values or status indicators rather than raw data streams.
        They display point-in-time metrics or status snapshots.

        Note:
            Mutually exclusive with :attr:`is_data_bound` - a widget type is
            either aggregation OR data-bound, never both. All defined widget
            types fall into exactly one of these two categories.

        Returns:
            True if the widget displays aggregated data (METRIC_CARD,
            STATUS_GRID), False otherwise (CHART, TABLE, EVENT_FEED).
        """
        return self in {
            EnumWidgetType.METRIC_CARD,
            EnumWidgetType.STATUS_GRID,
        }
