#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Hub WebSocket Endpoint Model.

Strongly-typed model for WebSocket endpoint configuration in hubs.
"""

from pydantic import BaseModel, Field


class ModelHubWebSocketEndpoint(BaseModel):
    """WebSocket endpoint configuration for hubs."""

    path: str = Field(default=..., description="WebSocket path")
    description: str | None = Field(default=None, description="WebSocket description")
