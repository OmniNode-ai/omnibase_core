# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic models for the no-plugin-daemon-classes COMPUTE validator (OMN-13309).

These models live in validation/ (which carries the legacy disallow_any_explicit=False
mypy override) because Pydantic's BaseModel is generic and triggers explicit-any
in the stricter validators/ directory.

Input/output types for HandlerNoPluginDaemonClasses are imported from here.
"""

from __future__ import annotations

__all__ = [
    "ModelNoPluginDaemonFinding",
    "ModelNoPluginDaemonInput",
    "ModelNoPluginDaemonResult",
]

from pydantic import BaseModel, ConfigDict, Field


class ModelNoPluginDaemonFinding(BaseModel):
    """A banned Plugin* lifecycle class found in source."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(..., description="File path as string")
    line: int = Field(..., description="1-based line number of the class definition")
    column: int = Field(..., description="0-based column offset")
    class_name: str = Field(..., description="Name of the offending class")
    bases: tuple[str, ...] = Field(default=(), description="Base class names")
    reason: str = Field(..., description="Human-readable reason for the finding")

    def format(self) -> str:
        """Return a human-readable one-line summary of this finding."""
        bases = ", ".join(self.bases) if self.bases else "<no bases>"
        return (
            f"{self.path}:{self.line}:{self.column + 1}: {self.class_name} "
            f"uses Plugin* lifecycle ownership ({self.reason}); bases: {bases}"
        )


class ModelNoPluginDaemonInput(BaseModel):
    """Payload for a no-plugin-daemon validation request.

    The caller (EFFECT boundary) is responsible for reading file contents and
    supplying them here.  The handler performs no filesystem I/O.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[tuple[str, str], ...] = Field(
        ...,
        description=(
            "Sequence of (path_str, source_text) pairs to validate. "
            "path_str is used only for finding labels; source_text is the UTF-8 content."
        ),
    )


class ModelNoPluginDaemonResult(BaseModel):
    """Result of a no-plugin-daemon validation pass."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelNoPluginDaemonFinding, ...] = Field(
        default=(),
        description="All lifecycle violations found; empty means clean.",
    )

    @property
    def is_clean(self) -> bool:
        """True when no violations were found."""
        return len(self.findings) == 0
