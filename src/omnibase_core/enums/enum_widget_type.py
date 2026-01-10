# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Widget type enumeration for dashboard widgets."""

from enum import Enum

__all__ = ["EnumWidgetType"]


class EnumWidgetType(str, Enum):
    """Dashboard widget type values.

    Defines the types of widgets available for dashboard configuration.
    Each type has specific configuration requirements and rendering behavior.
    """

    CHART = "chart"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    STATUS_GRID = "status_grid"
    EVENT_FEED = "event_feed"

    @property
    def is_data_bound(self) -> bool:
        """Check if widget type requires data binding."""
        return self in {
            EnumWidgetType.CHART,
            EnumWidgetType.TABLE,
            EnumWidgetType.EVENT_FEED,
        }

    @property
    def is_aggregation(self) -> bool:
        """Check if widget displays aggregated metrics."""
        return self in {
            EnumWidgetType.METRIC_CARD,
            EnumWidgetType.STATUS_GRID,
        }
