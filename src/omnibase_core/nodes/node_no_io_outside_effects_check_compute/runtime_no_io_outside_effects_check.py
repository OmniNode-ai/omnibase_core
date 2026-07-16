# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-io-outside-effects check — pre-commit hook + CI gate.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoIoOutsideEffectsCheckCompute``) — DRY per the OMN-13305 pattern,
following the ``node_no_raw_sqlite3_check_compute`` template (OMN-14659): a
single module owns the pure handler dispatch plus a synchronous CLI ``main()``
that performs all filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): pre-commit hands us staged files
  (``.py`` and/or ``contract.yaml``). Because the rule keys off the sibling
  ``contract.yaml`` archetype, a bare handler edit is not enough context — so
  for each staged file we resolve its node-package directory (the parent dir
  containing a ``contract.yaml``) and gather that ``contract.yaml`` plus every
  ``.py`` file in it. Staged files whose directory has no ``contract.yaml`` are
  not node packages and are skipped.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks ``--root``
  (default ``src``) via the paired ``node_source_file_gather_effect`` EFFECT
  node, gathering both ``**/*.py`` and ``**/contract.yaml`` so the COMPUTE can
  group by directory and scan only the non-EFFECT packages.

Usage::

    python -m omnibase_core.nodes.node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check file1.py contract.yaml
    python -m omnibase_core.nodes.node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check
    python -m omnibase_core.nodes.node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check --root src

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14694 (WS8 seed) → OMN-14662 (archetype-purity collapse).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_io_outside_effects_check.model_no_io_outside_effects_check_input import (
    ModelNoIoOutsideEffectsCheckInput,
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
from omnibase_core.nodes.node_no_io_outside_effects_check_compute.archetype_resolver import (
    CONTRACT_FILENAME,
)
from omnibase_core.nodes.node_no_io_outside_effects_check_compute.handler import (
    NodeNoIoOutsideEffectsCheckCompute,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

__all__ = ["main"]

_DEFAULT_ROOT: Final[str] = "src"


def _read_node_dir(node_dir: Path) -> tuple[list[ModelSourceFile], list[str]]:
    """Gather a node package's contract.yaml + .py modules from disk."""
    files: list[ModelSourceFile] = []
    read_errors: list[str] = []
    for member in sorted(node_dir.iterdir()):
        if not member.is_file():
            continue
        if member.name != CONTRACT_FILENAME and member.suffix != ".py":
            continue
        try:
            source = member.read_text(encoding="utf-8")
        except OSError as exc:
            read_errors.append(f"{member}: read error: {exc}")
            continue
        files.append(ModelSourceFile(path=str(member), source=source))
    return files, read_errors


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Resolves each staged file's node-package directory (parent dir containing a
    ``contract.yaml``) and gathers that whole package once, so the pure handler
    always has the archetype seam alongside the modules to scan. Staged files
    outside any node package are skipped.
    """
    files: list[ModelSourceFile] = []
    read_errors: list[str] = []
    seen_dirs: set[Path] = set()
    for path in paths:
        node_dir = path.parent
        if node_dir in seen_dirs:
            continue
        if not (node_dir / CONTRACT_FILENAME).is_file():
            continue
        seen_dirs.add(node_dir)
        dir_files, dir_errors = _read_node_dir(node_dir)
        files.extend(dir_files)
        read_errors.extend(dir_errors)
    return files, read_errors


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only tree walk in this module — delegated
    to the paired canonical node. Both ``**/*.py`` and ``**/contract.yaml`` are
    gathered so the COMPUTE can group modules by their node package.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=root, include_patterns=["**/*.py", f"**/{CONTRACT_FILENAME}"]
        )
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
    return NodeNoIoOutsideEffectsCheckCompute().handle(
        ModelNoIoOutsideEffectsCheckInput(files=files)
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: pre-commit staged-file mode, or a full-tree walk with no args.

    Returns:
        0 on PASS, 1 on FAIL/ERROR.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-io-outside-effects",
        description=(
            "Detect forbidden I/O surfaces inside non-EFFECT node packages "
            "via the no-io-outside-effects COMPUTE node (OMN-14694/OMN-14662)."
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
        print(  # print-ok: CLI output
            f"ERROR: Failed to read {len(read_errors)} file(s):"
        )
        for read_error in read_errors:
            print(f"  {read_error}")  # print-ok: CLI output
        return 1

    report = _run(files)

    if report.overall_status == "PASS":
        print(  # print-ok: CLI output
            "OK: No forbidden I/O found in non-EFFECT node packages"
        )
        return 0

    print(  # print-ok: CLI output
        f"FAIL: Found {report.metrics.total} I/O-outside-EFFECT violation(s) "
        "in non-EFFECT node packages:"
    )
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    print(  # print-ok: CLI output
        "\nOnly EFFECT nodes may perform I/O — COMPUTE / REDUCER / ORCHESTRATOR "
        "packages must be pure."
        "\nMove the I/O into a dedicated EFFECT node (inject adapters/buses via DI)."
        "\nAdd '# io-ok: <reason>' to suppress a proven-legitimate exception."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
