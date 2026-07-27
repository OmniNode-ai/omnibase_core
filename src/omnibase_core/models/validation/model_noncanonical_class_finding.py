# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelNoncanonicalClassFinding — finding from the non-canonical lifecycle-class ratchet (OMN-14350)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelNoncanonicalClassFinding:
    """A class whose CamelCase name carries a non-canonical lifecycle type-word.

    ``severity`` is ``"hardfail"`` for a public class that is a ratchet candidate
    (gate-blocking unless allowlisted) and ``"soft"`` for an underscore-private
    class (report-only, never gate-blocking).
    """

    path: Path
    line: int
    column: int
    class_name: str
    module: str
    matched_word: str
    severity: str

    @property
    def fqn(self) -> str:
        """Fully-qualified ``module:ClassName`` identity used by the allowlist."""
        return f"{self.module}:{self.class_name}"

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column + 1}: {self.class_name} "
            f"carries non-canonical type-word '{self.matched_word}' "
            f"({self.severity}); fqn: {self.fqn}"
        )
