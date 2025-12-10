#!/usr/bin/env python3
"""
Hub HTTP Endpoint Model.

Strongly-typed model for HTTP endpoint configuration in hubs.
"""

from pydantic import BaseModel, Field


class ModelHubHttpEndpoint(BaseModel):
    """HTTP endpoint configuration for hubs."""

    path: str = Field(default=..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    description: str | None = Field(default=None, description="Endpoint description")
