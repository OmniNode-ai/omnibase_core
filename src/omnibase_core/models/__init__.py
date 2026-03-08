# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Package init kept intentionally light to avoid circular imports during
# submodule imports (e.g., utils → models.common → package init → cli → utils).
# Importing heavy subpackages or re-exporting symbols here can trigger cycles.

"""
OmniBase Core Models

Organized by domain for better maintainability and discoverability.
This package __init__ avoids importing subpackages at import time to
prevent circular import chains.
"""

# Expose names for discoverability without importing subpackages at runtime.
# Callers should import concrete symbols from their modules directly, e.g.:
#   from omnibase_core.models.common.model_error_context import ModelErrorContext

__all__ = [
    # Domain modules (names only; no runtime import here)
    "agent",  # Agent status and lifecycle models (OMN-1847)
    "cli",
    "common",
    "config",
    "connections",
    "context",
    "contracts",
    "core",
    "dedup",
    "epic",  # Epic-team execution state models (OMN-3871)
    "events",
    "execution",
    "handlers",
    "hooks",  # External hook models (Claude Code - OMN-1474)
    "infrastructure",
    "intelligence",  # AI/ML intelligence models (OMN-1490)
    "mcp",  # MCP (Model Context Protocol) models (OMN-1286)
    "merge",  # Contract merge and geometric conflict models (OMN-1127, OMN-1853)
    "metadata",
    "nodes",
    "notifications",
    "operations",
    "pattern_learning",  # Pattern learning models (OMN-1683)
    "plan",  # Plan parsing models (OMN-3868)
    "pipeline",
    "projection",
    "providers",
    "registration",
    "results",
    "routing",  # Tiered resolution routing models (OMN-2890)
    "skill",  # Skill execution result models (OMN-3867)
    "state",
    "ticket",  # Ticket contract and context bundle models (OMN-3104)
    "validation",
]
