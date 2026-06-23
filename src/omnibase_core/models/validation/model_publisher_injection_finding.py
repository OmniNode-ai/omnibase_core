# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelPublisherInjectionFinding — finding from the publisher injection gate (OMN-12881)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelPublisherInjectionFinding:
    """A single finding from the publisher injection gate validator."""

    path: Path
    line: int
    column: int
    rule: str
    message: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column + 1}: [{self.rule}] {self.message}"
        )
