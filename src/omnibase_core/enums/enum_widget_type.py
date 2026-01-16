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

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ("EnumWidgetType",)


@unique
class EnumWidgetType(StrValueHelper, str, Enum):
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

    @property
    def is_data_bound(self) -> bool:
        """Check if widget type requires external data binding.

        Data-bound widgets (CHART, TABLE, EVENT_FEED) display real-time or
        historical data from external sources. They need continuous data
        updates and typically subscribe to a data source for real-time updates.

        Note:
            Mutually exclusive with :attr:`is_aggregation` - a widget type is
            either data-bound OR aggregation, never both. All defined widget
            types fall into exactly one of these two categories.

        Returns:
            True if the widget type requires data binding (CHART, TABLE,
            EVENT_FEED), False otherwise (METRIC_CARD, STATUS_GRID).
        """
        return self in {
            EnumWidgetType.CHART,
            EnumWidgetType.TABLE,
            EnumWidgetType.EVENT_FEED,
        }

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
