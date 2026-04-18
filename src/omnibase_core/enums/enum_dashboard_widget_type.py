# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Widget types a projection may declare for dashboard rendering."""

from __future__ import annotations

from enum import StrEnum


class EnumDashboardWidgetType(StrEnum):
    TILE = "tile"
    CHART = "chart"
    TABLE = "table"
    LIST = "list"
    SCALAR = "scalar"
