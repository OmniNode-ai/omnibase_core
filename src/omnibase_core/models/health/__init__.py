"""
Health domain models for ONEX.
"""

from .model_baseline_health_report import ModelBaselineHealthReport
from .model_health_attributes import ModelHealthAttributes
from .model_health_check import ModelHealthCheck
from .model_health_check_config import ModelHealthCheckConfig
from .model_health_check_metadata import ModelHealthCheckMetadata
from .model_health_issue import ModelHealthIssue
from .model_health_metadata import ModelHealthMetadata
from .model_health_metric import ModelHealthMetric
from .model_health_metrics import ModelHealthMetrics
from .model_health_status import ModelHealthStatus
from .model_invariant_status import ModelInvariantStatus
from .model_performance_metrics import ModelPerformanceMetrics
from .model_tool_health import ModelToolHealth

__all__: list[str] = [
    "ModelBaselineHealthReport",
    "ModelHealthAttributes",
    "ModelHealthCheck",
    "ModelHealthCheckConfig",
    "ModelHealthCheckMetadata",
    "ModelHealthIssue",
    "ModelHealthMetadata",
    "ModelHealthMetric",
    "ModelHealthMetrics",
    "ModelHealthStatus",
    "ModelInvariantStatus",
    "ModelPerformanceMetrics",
    "ModelToolHealth",
]

# Fix forward references for Pydantic models.
# These rebuilds are needed to resolve self-referential type annotations.
try:
    ModelHealthStatus.model_rebuild()
    ModelToolHealth.model_rebuild()
except Exception:
    # init-errors-ok: model_rebuild may fail during circular import resolution, safe to ignore
    pass

# Resolve forward reference for ModelHealthCheckMetadata.custom_fields
# This is needed because ModelCustomFields is imported with TYPE_CHECKING guard
# to break the circular import chain: services → ... → health → services
# We also need to rebuild ModelHealthCheckConfig since it contains ModelHealthCheckMetadata
try:
    from omnibase_core.models.services.model_custom_fields import (
        ModelCustomFields as _ModelCustomFields,
    )

    # Rebuild in dependency order: ModelHealthCheckMetadata first (has forward ref),
    # then ModelHealthCheckConfig (contains ModelHealthCheckMetadata)
    # Use explicit namespace to ensure the forward reference is resolved
    ModelHealthCheckMetadata.model_rebuild(
        _types_namespace={"ModelCustomFields": _ModelCustomFields}
    )
    ModelHealthCheckConfig.model_rebuild()
except Exception:
    # init-errors-ok: model_rebuild may fail during circular import resolution, safe to ignore
    pass
