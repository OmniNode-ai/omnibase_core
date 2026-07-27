# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGitSubprocessFinding — finding from the unguarded-git-subprocess guard (OMN-14891)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelGitSubprocessFinding:
    """An unguarded ``git`` subprocess invocation found in a test file."""

    path: Path
    line: int
    column: int
    call: str
    reason: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column + 1}: {self.call}(...) shells out to "
            f"git without a scrubbed env ({self.reason})"
        )
