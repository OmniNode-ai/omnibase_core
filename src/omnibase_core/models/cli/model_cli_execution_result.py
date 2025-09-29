"""
Model for CLI execution results.

This module provides the CLI execution result type using the enhanced
ModelExecutionResult as the underlying implementation.
"""

from __future__ import annotations

from omnibase_core.models.infrastructure.model_execution_result import (
    ModelExecutionResult,
)

from .model_cli_output_data import ModelCliOutputData

# CLI execution result type alias
ModelCliExecutionResult = ModelExecutionResult[ModelCliOutputData, str]


# Export for use
__all__ = [
    "ModelCliExecutionResult",
]
