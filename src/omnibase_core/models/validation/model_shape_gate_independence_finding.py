# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelShapeGateIndependenceFinding — finding from the shape-gate independence guard (OMN-20298)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelShapeGateIndependenceFinding:
    """A shape-gate detector job whose result depends on the change-control preflight."""

    path: Path
    job: str
    reason: str

    def format(self) -> str:
        return f"{self.path}: job '{self.job}' {self.reason}"
