from uuid import UUID

from pydantic import Field

__all__ = [
    "ModelDiscoveryRequestModelMetadata",
    "ModelDiscoveryResponseModelMetadata",
]

"""
Discovery Request and Response Metadata Models

Type-safe metadata for discovery protocol request/response patterns.
"""

from typing import Any

from pydantic import BaseModel

from .model_discoveryresponsemetadata import ModelDiscoveryResponseModelMetadata


class ModelDiscoveryRequestModelMetadata(BaseModel):
    """Metadata for discovery request messages."""

    request_id: UUID = Field(default=..., description="Unique request identifier")
    node_types: list[str] | None = Field(
        default=None, description="Filter by node types (COMPUTE, EFFECT, etc.)"
    )
    requested_capabilities: list[str] | None = Field(
        default=None, description="Filter by required capabilities"
    )
    filter_criteria: dict[str, Any] | None = Field(
        default=None, description="Additional filter criteria"
    )
