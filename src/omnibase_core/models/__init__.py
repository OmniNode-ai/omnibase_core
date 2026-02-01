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
    "cli",
    "common",
    "config",
    "connections",
    "context",
    "contracts",
    "core",
    "dedup",
    "events",
    "execution",
    "handlers",
    "hooks",  # External hook models (Claude Code - OMN-1474)
    "infrastructure",
    "intelligence",  # AI/ML intelligence models (OMN-1490)
    "mcp",  # MCP (Model Context Protocol) models (OMN-1286)
    "metadata",
    "nodes",
    "notifications",
    "operations",
    "pattern_learning",  # Pattern learning models (OMN-1683)
    "pipeline",
    "projection",
    "providers",
    "registration",
    "results",
    "state",
    "validation",
]
