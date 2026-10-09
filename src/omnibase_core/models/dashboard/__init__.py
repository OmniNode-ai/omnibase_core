# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dashboard models and widget configuration types.

Pydantic models for configuring dashboards and their
widgets in the ONEX platform. The dashboard system follows a hierarchical
structure:

- **Dashboard Config**: Top-level container with layout and theme settings
- **Widget Definition**: Individual widget with position, size, and config
- **Widget Config**: Type-specific configuration (chart, table, metric, etc.)
- **View Models**: Lightweight projections for UI rendering (NodeView, CapabilityView)

Widget Types:
    - **Chart**: Line, bar, area, pie, and scatter visualizations
    - **Table**: Paginated, sortable tabular data display
    - **Metric Card**: Single KPI display with trend and thresholds
    - **Status Grid**: Multi-item health/status indicators
    - **Event Feed**: Real-time event stream with filtering

Example:
    Create a simple dashboard with a metric card widget::

        from uuid import uuid4
        from omnibase_core.models.dashboard import (
            ModelDashboardConfig,
            ModelWidgetDefinition,
            ModelWidgetConfigMetricCard,
        )

        dashboard = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="System Health",
            widgets=(
                ModelWidgetDefinition(
                    widget_id=uuid4(),
                    title="CPU Usage",
                    config=ModelWidgetConfigMetricCard(
                        metric_key="cpu_percent",
                        label="CPU",
                        unit="%",
                        format="number",
                    ),
                ),
            ),
        )

See Also:
    - :class:`~omnibase_core.enums.EnumWidgetType`: Widget type enumeration
    - :class:`~omnibase_core.enums.EnumDashboardTheme`: Theme options
    - :class:`~omnibase_core.enums.EnumDashboardStatus`: Lifecycle states
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_binding_order_direction import (
        EnumBindingOrderDirection,
    )
    from omnibase_core.models.dashboard.model_action_contract import ModelActionContract
    from omnibase_core.models.dashboard.model_action_gate_policy import (
        ModelActionGatePolicy,
    )
    from omnibase_core.models.dashboard.model_capability_view import ModelCapabilityView
    from omnibase_core.models.dashboard.model_chart_axis_config import (
        ModelChartAxisConfig,
    )
    from omnibase_core.models.dashboard.model_chart_series_config import (
        ModelChartSeriesConfig,
    )
    from omnibase_core.models.dashboard.model_component_contract import (
        ModelComponentContract,
    )
    from omnibase_core.models.dashboard.model_dashboard_config import (
        ModelDashboardConfig,
    )
    from omnibase_core.models.dashboard.model_dashboard_layout_config import (
        ModelDashboardLayoutConfig,
    )
    from omnibase_core.models.dashboard.model_data_binding_contract import (
        ModelDataBindingContract,
    )
    from omnibase_core.models.dashboard.model_event_filter import ModelEventFilter
    from omnibase_core.models.dashboard.model_evidence_requirement_contract import (
        ModelEvidenceRequirementContract,
    )
    from omnibase_core.models.dashboard.model_metric_threshold import (
        ModelMetricThreshold,
    )
    from omnibase_core.models.dashboard.model_node_view import ModelNodeView
    from omnibase_core.models.dashboard.model_omnistudio_evidence_bundle import (
        ModelOmniStudioEvidenceBundle,
    )
    from omnibase_core.models.dashboard.model_permission_contract import (
        ModelPermissionContract,
    )
    from omnibase_core.models.dashboard.model_renderer_capability_contract import (
        ModelRendererCapabilityContract,
    )
    from omnibase_core.models.dashboard.model_renderer_theme_contract import (
        ModelRendererThemeContract,
    )
    from omnibase_core.models.dashboard.model_review_packet import ModelReviewPacket
    from omnibase_core.models.dashboard.model_severity_role import (
        DEFAULT_SEVERITY_ROLES,
        ModelSeverityRole,
    )
    from omnibase_core.models.dashboard.model_severity_verdict import (
        ModelSeverityVerdict,
    )
    from omnibase_core.models.dashboard.model_status_item_config import (
        ModelStatusItemConfig,
    )
    from omnibase_core.models.dashboard.model_status_secondary import (
        ModelStatusSecondary,
    )
    from omnibase_core.models.dashboard.model_table_column_config import (
        ModelTableColumnConfig,
    )
    from omnibase_core.models.dashboard.model_theme_activation import (
        ModelThemeActivation,
    )
    from omnibase_core.models.dashboard.model_theme_catalog import ModelThemeCatalog
    from omnibase_core.models.dashboard.model_theme_catalog_entry import (
        ModelThemeCatalogEntry,
    )
    from omnibase_core.models.dashboard.model_theme_instance import ModelThemeInstance
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
    from omnibase_core.models.dashboard.model_widget_definition import (
        ModelWidgetConfig,
        ModelWidgetDefinition,
    )
    from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
    from omnibase_core.models.dashboard.model_widget_provenance import (
        ModelWidgetProvenance,
    )

__all__: tuple[str, ...] = (
    # Theme contract, instances, and catalog (OMN-13389 / OMN-16882)
    "ModelThemeActivation",
    "ModelThemeCatalog",
    "ModelThemeCatalogEntry",
    "ModelThemeInstance",
    # Dashboard Configuration
    "ModelDashboardConfig",
    "ModelDashboardLayoutConfig",
    # Widget Definition
    "ModelWidgetConfig",
    "ModelWidgetDefinition",
    # View Models
    "ModelCapabilityView",
    "ModelNodeView",
    # Chart Widget
    "ModelChartAxisConfig",
    "ModelChartSeriesConfig",
    "ModelWidgetConfigChart",
    # Table Widget
    "ModelTableColumnConfig",
    "ModelWidgetConfigTable",
    # Metric Card Widget
    "ModelMetricThreshold",
    "ModelWidgetConfigMetricCard",
    # Status Grid Widget + semantic severity (OMN-16884 — Phase C3)
    "ModelStatusItemConfig",
    "ModelWidgetConfigStatusGrid",
    "DEFAULT_SEVERITY_ROLES",
    "ModelSeverityRole",
    "ModelSeverityVerdict",
    "ModelStatusSecondary",
    # Event Feed Widget
    "ModelEventFilter",
    "ModelWidgetConfigEventFeed",
    # UI Contract Primitives (OMN-13130 — Phase 0)
    "ModelComponentContract",
    "ModelActionContract",
    "ModelActionGatePolicy",
    "ModelDataBindingContract",
    "EnumBindingOrderDirection",
    "ModelPermissionContract",
    "ModelEvidenceRequirementContract",
    "ModelRendererCapabilityContract",
    # Versioned design-token contract (OMN-13389)
    "ModelRendererThemeContract",
    # One versioned widget envelope — the unit Plane 1 distributes
    # (OMN-16883, Phase C2)
    "ModelWidgetEnvelope",
    "ModelWidgetProvenance",
    # Review Packet + OmniStudio Evidence Bundle (OMN-13387)
    "ModelReviewPacket",
    "ModelOmniStudioEvidenceBundle",
)


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumBindingOrderDirection": (
        "omnibase_core.enums.enum_binding_order_direction",
        "EnumBindingOrderDirection",
    ),
    "ModelActionContract": (
        "omnibase_core.models.dashboard.model_action_contract",
        "ModelActionContract",
    ),
    "ModelActionGatePolicy": (
        "omnibase_core.models.dashboard.model_action_gate_policy",
        "ModelActionGatePolicy",
    ),
    "ModelCapabilityView": (
        "omnibase_core.models.dashboard.model_capability_view",
        "ModelCapabilityView",
    ),
    "ModelChartAxisConfig": (
        "omnibase_core.models.dashboard.model_chart_axis_config",
        "ModelChartAxisConfig",
    ),
    "ModelChartSeriesConfig": (
        "omnibase_core.models.dashboard.model_chart_series_config",
        "ModelChartSeriesConfig",
    ),
    "ModelComponentContract": (
        "omnibase_core.models.dashboard.model_component_contract",
        "ModelComponentContract",
    ),
    "ModelDashboardConfig": (
        "omnibase_core.models.dashboard.model_dashboard_config",
        "ModelDashboardConfig",
    ),
    "ModelDashboardLayoutConfig": (
        "omnibase_core.models.dashboard.model_dashboard_layout_config",
        "ModelDashboardLayoutConfig",
    ),
    "ModelDataBindingContract": (
        "omnibase_core.models.dashboard.model_data_binding_contract",
        "ModelDataBindingContract",
    ),
    "ModelEventFilter": (
        "omnibase_core.models.dashboard.model_event_filter",
        "ModelEventFilter",
    ),
    "ModelEvidenceRequirementContract": (
        "omnibase_core.models.dashboard.model_evidence_requirement_contract",
        "ModelEvidenceRequirementContract",
    ),
    "ModelMetricThreshold": (
        "omnibase_core.models.dashboard.model_metric_threshold",
        "ModelMetricThreshold",
    ),
    "ModelNodeView": (
        "omnibase_core.models.dashboard.model_node_view",
        "ModelNodeView",
    ),
    "ModelOmniStudioEvidenceBundle": (
        "omnibase_core.models.dashboard.model_omnistudio_evidence_bundle",
        "ModelOmniStudioEvidenceBundle",
    ),
    "ModelPermissionContract": (
        "omnibase_core.models.dashboard.model_permission_contract",
        "ModelPermissionContract",
    ),
    "ModelRendererCapabilityContract": (
        "omnibase_core.models.dashboard.model_renderer_capability_contract",
        "ModelRendererCapabilityContract",
    ),
    "ModelRendererThemeContract": (
        "omnibase_core.models.dashboard.model_renderer_theme_contract",
        "ModelRendererThemeContract",
    ),
    "ModelReviewPacket": (
        "omnibase_core.models.dashboard.model_review_packet",
        "ModelReviewPacket",
    ),
    "DEFAULT_SEVERITY_ROLES": (
        "omnibase_core.models.dashboard.model_severity_role",
        "DEFAULT_SEVERITY_ROLES",
    ),
    "ModelSeverityRole": (
        "omnibase_core.models.dashboard.model_severity_role",
        "ModelSeverityRole",
    ),
    "ModelSeverityVerdict": (
        "omnibase_core.models.dashboard.model_severity_verdict",
        "ModelSeverityVerdict",
    ),
    "ModelStatusItemConfig": (
        "omnibase_core.models.dashboard.model_status_item_config",
        "ModelStatusItemConfig",
    ),
    "ModelStatusSecondary": (
        "omnibase_core.models.dashboard.model_status_secondary",
        "ModelStatusSecondary",
    ),
    "ModelTableColumnConfig": (
        "omnibase_core.models.dashboard.model_table_column_config",
        "ModelTableColumnConfig",
    ),
    "ModelThemeActivation": (
        "omnibase_core.models.dashboard.model_theme_activation",
        "ModelThemeActivation",
    ),
    "ModelThemeCatalog": (
        "omnibase_core.models.dashboard.model_theme_catalog",
        "ModelThemeCatalog",
    ),
    "ModelThemeCatalogEntry": (
        "omnibase_core.models.dashboard.model_theme_catalog_entry",
        "ModelThemeCatalogEntry",
    ),
    "ModelThemeInstance": (
        "omnibase_core.models.dashboard.model_theme_instance",
        "ModelThemeInstance",
    ),
    "ModelWidgetConfigChart": (
        "omnibase_core.models.dashboard.model_widget_config_chart",
        "ModelWidgetConfigChart",
    ),
    "ModelWidgetConfigEventFeed": (
        "omnibase_core.models.dashboard.model_widget_config_event_feed",
        "ModelWidgetConfigEventFeed",
    ),
    "ModelWidgetConfigMetricCard": (
        "omnibase_core.models.dashboard.model_widget_config_metric_card",
        "ModelWidgetConfigMetricCard",
    ),
    "ModelWidgetConfigStatusGrid": (
        "omnibase_core.models.dashboard.model_widget_config_status_grid",
        "ModelWidgetConfigStatusGrid",
    ),
    "ModelWidgetConfigTable": (
        "omnibase_core.models.dashboard.model_widget_config_table",
        "ModelWidgetConfigTable",
    ),
    "ModelWidgetConfig": (
        "omnibase_core.models.dashboard.model_widget_definition",
        "ModelWidgetConfig",
    ),
    "ModelWidgetDefinition": (
        "omnibase_core.models.dashboard.model_widget_definition",
        "ModelWidgetDefinition",
    ),
    "ModelWidgetEnvelope": (
        "omnibase_core.models.dashboard.model_widget_envelope",
        "ModelWidgetEnvelope",
    ),
    "ModelWidgetProvenance": (
        "omnibase_core.models.dashboard.model_widget_provenance",
        "ModelWidgetProvenance",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
