# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Widget definition model with discriminated union config."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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

__all__ = ["ModelWidgetDefinition", "ModelWidgetConfig"]


# Discriminated union of all widget config types
ModelWidgetConfig = Annotated[
    ModelWidgetConfigChart
    | ModelWidgetConfigTable
    | ModelWidgetConfigMetricCard
    | ModelWidgetConfigStatusGrid
    | ModelWidgetConfigEventFeed,
    Field(discriminator="config_kind"),
]


class ModelWidgetDefinition(BaseModel):
    """Widget definition for dashboard configuration.

    Wraps a widget config with metadata like id, title, and position.
    The config field is a discriminated union based on config_kind.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    widget_id: UUID = Field(..., description="Unique widget identifier")
    title: str = Field(..., min_length=1, description="Widget display title")
    config: ModelWidgetConfig = Field(..., description="Widget-specific configuration")

    # Layout positioning (grid-based)
    row: int = Field(default=0, ge=0, description="Grid row position")
    col: int = Field(default=0, ge=0, description="Grid column position")
    width: int = Field(default=1, ge=1, le=12, description="Grid column span")
    height: int = Field(default=1, ge=1, description="Grid row span")

    # Optional metadata
    description: str | None = Field(default=None, description="Widget description")
    data_source: str | None = Field(default=None, description="Data source identifier")
    extra_config: dict[str, str] | None = Field(
        default=None, description="Extension config (string values only)"
    )
