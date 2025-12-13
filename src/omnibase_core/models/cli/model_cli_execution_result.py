"""
Model for CLI execution results.

This module provides the CLI execution result type using the simple
ModelToolExecutionResult as the underlying implementation.
"""

from __future__ import annotations

from omnibase_core.models.tools.model_tool_execution_result import (
    ModelToolExecutionResult,
)

# CLI execution result type alias
ModelCliExecutionResult = ModelToolExecutionResult

# Export for use
__all__ = [
    "ModelCliExecutionResult",
]
