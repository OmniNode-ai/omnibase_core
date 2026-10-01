# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeFinding — finding from the canonical-file-shape ratchet (OMN-20304)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelCanonicalFileShapeFinding:
    """A file the canonical-file-shape ratchet refuses, with the rule it broke."""

    path: str
    rule: str
    reason: str

    def format(self) -> str:
        return f"{self.path}: [{self.rule}] {self.reason}"
