"""
Health domain models for ONEX.
"""

from .model_health_attributes import *
from .model_health_check import *
from .model_health_check_config import *
from .model_health_check_metadata import *
from .model_health_issue import *
from .model_health_metadata import *
from .model_health_metric import *
from .model_health_metrics import *
from .model_health_status import *
from .model_tool_health import *

__all__ = []

# Fix forward references for Pydantic models
try:
    from omnibase_core.model.health.model_tool_health import ModelToolHealth

    ModelToolHealth.model_rebuild()
except Exception:
    pass  # Ignore rebuild errors during import
