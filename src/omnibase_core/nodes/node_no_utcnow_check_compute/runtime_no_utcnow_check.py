# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-utcnow check — pre-commit hook + CI entrypoint.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoUtcnowCheckCompute``) — DRY per the OMN-13305 pattern
(``omnibase_core.validation.validator_backend_secret_discipline``): a single
module owns the pure handler plus a synchronous CLI ``main()`` that performs
all filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): the staged files pre-commit hands us
  are read directly here — no directory walk needed, matching the
  ``check-backend-secret-discipline`` precedent.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks
  ``--root`` (default ``src``) via the paired ``node_source_file_gather_effect``
  EFFECT node, reproducing the oracle CI gate's whole-tree scan
  (``omniclaude/scripts/validation/validate_no_utcnow.py`` ``src_root.rglob("*.py")``).

Usage::

    python -m omnibase_core.nodes.node_no_utcnow_check_compute.runtime_no_utcnow_check file1.py file2.py
    python -m omnibase_core.nodes.node_no_utcnow_check_compute.runtime_no_utcnow_check
    python -m omnibase_core.nodes.node_no_utcnow_check_compute.runtime_no_utcnow_check --root src

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14656 (RSD canary — Characterize -> Generate two-node split).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input import (
    ModelNoUtcnowCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_utcnow_check_compute.handler import (
    NodeNoUtcnowCheckCompute,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

__all__ = ["main"]

_DEFAULT_ROOT: Final[str] = "src"


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Non-``.py`` and missing paths are intentionally skipped. Read errors on
    existing Python files are returned as fatal diagnostics so the runtime does
    not report PASS with unscanned source.
    """
    files: list[ModelSourceFile] = []
    read_errors: list[str] = []
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            read_errors.append(f"{path}: read error: {exc}")
            continue
        files.append(ModelSourceFile(path=str(path), source=source))
    return files, read_errors


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only filesystem walk in this module —
    delegated to the paired canonical node rather than re-implemented here.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(root=root, include_patterns=["**/*.py"])
    )
    read_errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith(("read error:", "error checking file size:"))
    ]
    return [
        ModelSourceFile(path=f.path, source=f.source) for f in output.files
    ], read_errors


def _run(files: list[ModelSourceFile]) -> ModelValidationReport:
    """Dispatch gathered (path, source) pairs to the canonical COMPUTE node."""
    return NodeNoUtcnowCheckCompute().handle(ModelNoUtcnowCheckInput(files=files))


def main(argv: list[str] | None = None) -> int:
    """CLI entry: pre-commit staged-file mode, or a full-tree walk with no args.

    Returns:
        0 on PASS, 1 on FAIL/ERROR.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-utcnow",
        description=(
            "Detect datetime.utcnow() usage via the no-utcnow-check COMPUTE "
            "node (OMN-14656, revives OMN-2362)."
        ),
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help=(
            "Files to check (pre-commit passes staged filenames here). "
            "When omitted, walks --root recursively (CI / manual mode)."
        ),
    )
    parser.add_argument(
        "--root",
        default=_DEFAULT_ROOT,
        help=(
            "Root directory for a full-tree walk when no filenames are given "
            f"(default: {_DEFAULT_ROOT})"
        ),
    )
    parsed = parser.parse_args(argv)

    if parsed.filenames:
        files, read_errors = _gather_from_filenames([Path(f) for f in parsed.filenames])
    else:
        files, read_errors = _gather_from_root(parsed.root)

    if read_errors:
        print(
            f"ERROR: Failed to read {len(read_errors)} Python file(s):"
        )  # print-ok: CLI output
        for read_error in read_errors:
            print(f"  {read_error}")  # print-ok: CLI output
        return 1

    report = _run(files)

    if report.overall_status == "PASS":
        print("OK: No datetime.utcnow() usage found")  # print-ok: CLI output
        return 0

    summary = f"{report.overall_status}: Found {report.metrics.total} finding(s):\n"
    print(summary)  # print-ok: CLI output
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    remediation = (
        "\ndatetime.utcnow() produces timezone-naive datetimes and must not be used."
        "\nReplace with: datetime.now(tz=timezone.utc)  or  datetime.now(UTC)"
    )
    print(remediation)  # print-ok: CLI output
    return 1


if __name__ == "__main__":
    sys.exit(main())
