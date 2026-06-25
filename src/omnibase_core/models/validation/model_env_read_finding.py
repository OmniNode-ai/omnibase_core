# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Finding model for no-new-os-environ validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelEnvReadFinding:
    """One env-read violation found by the validator."""

    path: Path
    line: int
    col: int
    var_name: str
    raw_line: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.col}: "
            f"os.environ/os.getenv read of {self.var_name!r} "
            f"outside KEEP_ALLOWLIST"
        )
