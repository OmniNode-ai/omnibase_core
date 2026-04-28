# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""BaseGateCheck — abstract base for all substrate gate checks."""

from __future__ import annotations

import ast
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from omnibase_core.cli.substrate_gates.gate_violation import GateViolation

# Markers that suppress gate violations on the annotated line.
# Recognises: # substrate-allow: <reason>
#             # ONEX_EXCLUDE: <any>
#             # ai-slop-ok
_ALLOW_PATTERN = re.compile(
    r"#\s*(substrate-allow:|ONEX_EXCLUDE:|ai-slop-ok)",
    re.IGNORECASE,
)


def has_allow_annotation(source_lines: list[str], lineno: int) -> bool:
    """Return True if the source line carries a suppression annotation.

    Checks the line at *lineno* (1-based) for any recognised allow marker.
    Compatible with:
      - ``# substrate-allow: <reason>``
      - ``# ONEX_EXCLUDE: <reason>``
      - ``# ai-slop-ok``
    """
    if lineno < 1 or lineno > len(source_lines):
        return False
    line = source_lines[lineno - 1]
    return bool(_ALLOW_PATTERN.search(line))


class BaseGateCheck(ABC):
    """Abstract base for all substrate gate checks.

    Subclasses implement :meth:`check_tree` to emit :class:`GateViolation`
    objects; the base class handles file loading, parse-error safety, and
    empty-input short-circuiting.
    """

    @abstractmethod
    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        """Analyse *tree* and return any violations found."""

    def run(self, paths: list[Path]) -> list[GateViolation]:
        """Run the gate against every path in *paths*.

        Returns an empty list when *paths* is empty.  Parse errors are
        reported as violations so CI can surface them without crashing.
        """
        if not paths:
            return []

        violations: list[GateViolation] = []
        for path in paths:
            try:
                source = path.read_text(encoding="utf-8")
            except OSError as exc:
                violations.append(
                    GateViolation(path=path, line=0, message=f"cannot read file: {exc}")
                )
                continue

            source_lines = source.splitlines()

            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                violations.append(
                    GateViolation(
                        path=path,
                        line=exc.lineno or 0,
                        message=f"syntax error: {exc.msg}",
                    )
                )
                continue

            violations.extend(self.check_tree(tree, source_lines, path))

        return violations


def main_for_gate(gate: BaseGateCheck, argv: list[str] | None = None) -> int:
    """CLI entry point for a single gate.

    Accepts a list of file paths as positional arguments.
    Exits 0 when no violations are found, 1 otherwise.
    """
    args = argv if argv is not None else sys.argv[1:]
    paths = [Path(a) for a in args]
    violations = gate.run(paths)
    for v in violations:
        print(v, file=sys.stderr)  # print-ok: CLI violation reporting to stderr
    return 1 if violations else 0
