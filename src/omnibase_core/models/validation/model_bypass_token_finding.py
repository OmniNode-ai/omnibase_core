# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelBypassTokenFinding — finding from the bypass-token blocklist gate (OMN-13388)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelBypassTokenFinding:
    """A banned bypass token found in a scanned artifact."""

    path: Path
    line_number: int
    token: str
    line_text: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line_number}: bypass token {self.token!r} found: "
            f"{self.line_text.strip()!r}"
        )
