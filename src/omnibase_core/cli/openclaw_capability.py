# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dataclass for a single detected OpenClaw capability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpenClawCapability:
    """A single detected capability from an OpenClaw skill package."""

    category: str  # file_access, api_calls, shell_commands, env_vars, database, sdk
    details: str  # specific API/command/var detected
    security_tier: str  # safe, sandboxed, privileged, blocked
    source_line: int
    source_file: str
