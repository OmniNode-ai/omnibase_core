"""
Model for introspection command results.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_introspection_metadata import (
    ModelIntrospectionMetadata,
)
from omnibase_core.models.core.model_tool_health_status import ModelToolHealthStatus
from omnibase_core.models.core.model_usage_example import ModelUsageExample


class ModelIntrospectionResult(BaseModel):
    """Complete introspection result containing all introspection data."""

    metadata: ModelIntrospectionMetadata = Field(description="Tool metadata")
    health: ModelToolHealthStatus = Field(description="Tool health status")
    examples: list["ModelUsageExample[Any, Any]"] = Field(description="Usage examples")
