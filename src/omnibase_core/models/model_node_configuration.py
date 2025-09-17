"""
Model: Node Configuration
Domain: Core
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelNodeConfiguration(BaseModel):
    """
    Model for ONEX node configuration.

    Follows ONEX naming convention: Model{Entity}
    File naming: model_{entity}.py
    """

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(
        ..., description="ONEX node type (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)"
    )
    version: str = Field(..., description="Node version")
    enabled: bool = Field(default=True, description="Whether node is enabled")
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Node-specific configuration"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Node dependencies"
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
