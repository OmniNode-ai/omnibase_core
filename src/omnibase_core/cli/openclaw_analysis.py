# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dataclass for OpenClaw package analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.cli.openclaw_capability import OpenClawCapability


@dataclass
class OpenClawAnalysis:
    """Structured analysis result for an OpenClaw skill package."""

    name: str
    version: str
    description: str
    entry_point: str
    capabilities: list[OpenClawCapability] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)
    npm_dependencies: dict[str, str] = field(default_factory=dict)
    security_tier: str = "safe"
    confidence_level: str = "analyzable"
