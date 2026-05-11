# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHandlerDiGateFinding — finding from the handler DI gate validator (OMN-10726)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelHandlerDiGateFinding:
    """A single finding from the handler DI gate validator."""

    path: Path
    line: int
    column: int
    rule: str
    message: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column + 1}: [{self.rule}] {self.message}"
        )
