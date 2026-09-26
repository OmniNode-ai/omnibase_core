# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
MCP Security Summary Model.

Strongly typed model for MCP server security summary information.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.security.model_security_event import ModelSecurityEvent


class ModelMCPSecuritySummary(BaseModel):
    """MCP server security summary with strongly typed fields."""

    model_config = ConfigDict(extra="forbid")

    authentication_enabled: bool = Field(
        default=...,
        description="Whether authentication is enabled",
    )
    supported_auth_methods: list[str] = Field(
        default=...,
        description="List of supported authentication methods",
    )
    available_roles: list[str] = Field(
        default=..., description="List of available user roles"
    )
    security_events_count: int = Field(
        default=...,
        description="Total number of security events recorded",
    )
    last_events: list[ModelSecurityEvent] = Field(
        default=...,
        description="Recent security events",
    )
