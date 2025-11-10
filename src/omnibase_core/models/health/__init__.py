"""
Health domain models for ONEX.
"""

from .model_health_attributes import ModelHealthAttributes
from .model_health_check import ModelHealthCheck
from .model_health_check_config import ModelHealthCheckConfig
from .model_health_check_metadata import ModelHealthCheckMetadata
from .model_health_issue import ModelHealthIssue
from .model_health_metadata import ModelHealthMetadata
from .model_health_metric import ModelHealthMetric
from .model_health_metrics import ModelHealthMetrics
from .model_health_status import ModelHealthStatus
from .model_tool_health import ModelToolHealth

__all__: list[str] = [
    "ModelHealthAttributes",
    "ModelHealthCheck",
    "ModelHealthCheckConfig",
    "ModelHealthCheckMetadata",
    "ModelHealthIssue",
    "ModelHealthMetadata",
    "ModelHealthMetric",
    "ModelHealthMetrics",
    "ModelHealthStatus",
    "ModelToolHealth",
]

# Fix forward references for Pydantic models
try:
    from omnibase_core.models.health.model_tool_health import ModelToolHealth

    ModelToolHealth.model_rebuild()
except Exception:
    pass  # Ignore rebuild errors during import
