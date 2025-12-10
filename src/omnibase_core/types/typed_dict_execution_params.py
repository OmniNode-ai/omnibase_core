"""
Execution-related factory parameters.

Provides strong typing for execution results and parameters
using TypedDict for structural typing.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictExecutionParams(TypedDict, total=False):
    """Execution-related factory parameters.

    Provides strong typing for execution results including success status,
    exit codes, error messages, and generic data payloads.

    All fields are optional (total=False).
    """

    success: bool
    exit_code: int
    error_message: str
    data: object  # ONEX compliance - use object instead of Any for generic data


__all__ = ["TypedDictExecutionParams"]
