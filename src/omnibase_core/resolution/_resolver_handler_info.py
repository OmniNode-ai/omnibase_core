"""
Internal handler info type for ExecutionResolver.

This module contains a private data structure used internally by the
ExecutionResolver. This is not part of the public API.

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)


@dataclass
class _HandlerInfo:
    """Internal data structure for handler information during resolution."""

    handler_id: str
    priority: int
    tags: list[str]
    capability_outputs: list[str]
    has_must_run: bool
    constraints: ModelExecutionConstraints | None


__all__ = [
    "_HandlerInfo",
]
