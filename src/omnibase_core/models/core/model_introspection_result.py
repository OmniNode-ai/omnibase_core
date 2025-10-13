from typing import Any

from pydantic import Field

"""
Model for introspection command results.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_introspection_metadata import (
    ModelIntrospectionMetadata,
)
from omnibase_core.models.core.model_introspection_result_config import (
    ModelIntrospectionResultConfig,
)
from omnibase_core.models.core.model_tool_health_status import ModelToolHealthStatus
from omnibase_core.models.core.model_usage_example import ModelUsageExample


class ModelIntrospectionResult(BaseModel):
    """Complete introspection result containing all introspection data."""

    metadata: ModelIntrospectionMetadata = Field(description="Tool metadata")
    health: ModelToolHealthStatus = Field(description="Tool health status")
    examples: list["ModelUsageExample[Any, Any]"] = Field(description="Usage examples")
