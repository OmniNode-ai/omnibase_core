"""
MCP Security Summary Model.

Strongly typed model for MCP server security summary information.
"""

from typing import List

from pydantic import BaseModel, Field

from omnibase_core.model.security.model_security_event import \
    ModelSecurityEvent


class ModelMCPSecuritySummary(BaseModel):
    """MCP server security summary with strongly typed fields."""

    authentication_enabled: bool = Field(
        ..., description="Whether authentication is enabled"
    )
    supported_auth_methods: List[str] = Field(
        ..., description="List of supported authentication methods"
    )
    available_roles: List[str] = Field(..., description="List of available user roles")
    security_events_count: int = Field(
        ..., description="Total number of security events recorded"
    )
    last_events: List[ModelSecurityEvent] = Field(
        ..., description="Recent security events"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
