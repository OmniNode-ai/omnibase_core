# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST visitor that detects raw ``sqlite3.connect()`` calls.

Split out of ``handler.py`` (single-class-per-file, OMN-14656 convention) so
the COMPUTE handler module contains exactly one class
(``NodeNoRawSqlite3CheckCompute``).

Port of ``RawSqlite3Visitor`` + ``_call_has_annotation``
(``omniclaude/scripts/validation/validate_no_raw_sqlite3.py:52-118``).
Detects ``sqlite3.connect(...)`` (via ``import sqlite3``) and
``from sqlite3 import connect [as alias]; connect(...)`` / ``alias(...)``,
except where the call site carries a ``# di-ok`` annotation on its opening
line, closing line, or the line immediately preceding it.

File-level exclusion: files whose name ends in ``_adapter.py`` are the
authorised call site for a direct connection and are skipped entirely
(oracle ``EXCLUDED_FILENAME_PATTERNS``) — the caller-scoped ``CHECKED_DIRS``
/ ``tests/`` root-scoping in the oracle is a full-tree-walk concern, not
reproduced here (see the paired ``runtime_no_raw_sqlite3_check.py`` CLI's
``--root`` default for the generic equivalent).
"""

from __future__ import annotations

import ast
from pathlib import PurePosixPath
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = ["VALIDATOR_ID", "RawSqlite3Visitor", "is_excluded_adapter_filename"]

_SEVERITY_FAIL: Final = "FAIL"

VALIDATOR_ID: Final[str] = "arch-no-raw-sqlite3"
_REMEDIATION: Final[str] = "Add '# di-ok' to suppress for legitimate adapter bootstrap."

_FORBIDDEN_CALL: Final[str] = "connect"
_FORBIDDEN_MODULE: Final[str] = "sqlite3"
_EXCLUDED_FILENAME_SUFFIX: Final[str] = "_adapter.py"
_DI_OK_MARKER: Final[str] = "# di-ok"


def is_excluded_adapter_filename(path: str) -> bool:
    """Return True if ``path``'s filename ends in ``_adapter.py`` (oracle
    ``EXCLUDED_FILENAME_PATTERNS``) — the authorised direct-connection call site."""
    return PurePosixPath(path.replace("\\", "/")).name.endswith(
        _EXCLUDED_FILENAME_SUFFIX
    )


def _call_has_annotation(source_lines: list[str], node: ast.Call) -> bool:
    """Check if the call site has a ``# di-ok`` annotation.

    Checks the call's opening line, closing line (``end_lineno``), and the
    line immediately preceding the call — this handles ruff-reformatted
    multi-line calls where the trailing ``)`` lands on a different line from
    the function name.
    """
    candidates = {node.lineno}
    if hasattr(node, "end_lineno") and node.end_lineno:
        candidates.add(node.end_lineno)
    candidates.add(node.lineno - 1)
    for lineno in candidates:
        if (
            0 < lineno <= len(source_lines)
            and _DI_OK_MARKER in source_lines[lineno - 1]
        ):
            return True
    return False


class RawSqlite3Visitor(ast.NodeVisitor):
    """Walk an AST looking for raw ``sqlite3.connect()`` calls."""

    def __init__(self, path: str, source_lines: list[str]) -> None:
        self._path = path
        self._source_lines = source_lines
        self.findings: list[ModelValidationFinding] = []
        self._sqlite3_aliases: set[str] = set()
        self._sqlite3_connect_aliases: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == _FORBIDDEN_MODULE:
                self._sqlite3_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == _FORBIDDEN_MODULE:
            for alias in node.names:
                if alias.name == _FORBIDDEN_CALL:
                    self._sqlite3_connect_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        matched = False

        # sqlite3.connect(...)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == _FORBIDDEN_CALL
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self._sqlite3_aliases
        ):
            matched = True

        # from sqlite3 import connect [as alias]; connect(...) / alias(...)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in self._sqlite3_connect_aliases
        ):
            matched = True

        if matched and not _call_has_annotation(self._source_lines, node):
            self.findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity=_SEVERITY_FAIL,
                    location=f"{self._path}:{node.lineno}",
                    message=(
                        f"{self._path}:{node.lineno}: raw sqlite3.connect() call — "
                        "database access must go through an injected adapter, not a "
                        "direct connection. Add '# di-ok' to suppress for legitimate "
                        "adapter bootstrap."
                    ),
                    remediation=_REMEDIATION,
                )
            )

        self.generic_visit(node)
