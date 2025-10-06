#!/usr/bin/env python3
"""
Hub HTTP Endpoint Model - ONEX Standards Compliant.

Strongly-typed model for HTTP endpoint configuration in hubs.
"""

from pydantic import BaseModel, Field


class ModelHubHttpEndpoint(BaseModel):
    """HTTP endpoint configuration for hubs."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    description: str | None = Field(default=None, description="Endpoint description")
