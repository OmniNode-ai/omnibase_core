# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelPluginLifecycleFinding — finding from the Plugin* lifecycle guard (OMN-13284)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelPluginLifecycleFinding:
    """A banned Plugin* lifecycle class found in source."""

    path: Path
    line: int
    column: int
    class_name: str
    bases: tuple[str, ...]
    reason: str

    def format(self) -> str:
        bases = ", ".join(self.bases) if self.bases else "<no bases>"
        return (
            f"{self.path}:{self.line}:{self.column + 1}: {self.class_name} "
            f"uses Plugin* lifecycle ownership ({self.reason}); bases: {bases}"
        )
