# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-hardcoded-ip check — pre-commit hook + CI entrypoint.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoHardcodedIpCheckCompute``) — DRY per the OMN-13305 pattern, following
the ``node_no_utcnow_check_compute`` template (OMN-14656): a single module
owns the pure handler plus a synchronous CLI ``main()`` that performs all
filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): the staged files pre-commit hands us
  are read through the gather EFFECT node — no directory walk needed.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks each
  ``--root`` (default ``src``) via the paired ``node_source_file_gather_effect``
  EFFECT node for ``*.py``/``*.yaml``/``*.yml`` files, reproducing the oracle
  CI gate's file-type scope
  (``omniclaude/scripts/validation/validate_no_hardcoded_ip.py``).

  ``--root`` accepts **multiple** top-level roots (``nargs="+"``) — the oracle
  scanned three (``src``/``tests``/``scripts``); scanning only ``src`` was a
  scan-scope false-negative in which a non-allowlisted hardcoded IP under
  ``tests/`` or ``scripts/`` passed CI (OMN-14712). Each root is gathered
  independently (``ModelSourceFileGatherInput`` walks a single ``root``) and the
  eligible files are unioned before the pure COMPUTE dispatch. A non-existent
  root (e.g. ``scripts`` in a repo without one) gathers zero files rather than
  erroring, so the same invocation ports cleanly across repos.

  The omnibase_core CI self-scan currently passes ``--root src scripts`` (both
  clean). ``tests`` is not yet in the CI scope: it carries ~155 legitimate IP
  *fixtures* (this validator's own acceptance corpus among them) that need
  per-line ``# onex-allow-internal-ip`` triage before the required gate can scan
  it green — tracked as a follow-up to OMN-14712.

Usage::

    python -m omnibase_core.nodes.node_no_hardcoded_ip_check_compute.runtime_no_hardcoded_ip_check file1.py file2.yaml
    python -m omnibase_core.nodes.node_no_hardcoded_ip_check_compute.runtime_no_hardcoded_ip_check
    python -m omnibase_core.nodes.node_no_hardcoded_ip_check_compute.runtime_no_hardcoded_ip_check --root src tests scripts

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_hardcoded_ip_check.model_no_hardcoded_ip_check_input import (
    ModelNoHardcodedIpCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.handler import (
    NodeNoHardcodedIpCheckCompute,
)
from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.matcher_hardcoded_ip import (
    VALIDATOR_ID,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["main"]

_DEFAULT_ROOTS: Final[tuple[str, ...]] = ("src",)


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Non-Python/YAML and missing paths are intentionally skipped. Read errors
    on existing eligible files are returned as fatal diagnostics so the
    runtime does not report PASS with unscanned source.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=[str(path) for path in paths],
            include_patterns=["**/*.py", "**/*.yaml", "**/*.yml"],
        )
    )
    return _split_gather_output(output)


def _gather_from_roots(roots: list[str]) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only filesystem walk in this module —
    delegated to the paired canonical node rather than re-implemented here. Each
    root is gathered independently (the EFFECT node walks a single ``root``) and
    the eligible files are unioned so the CI self-scan can cover ``src``,
    ``tests``, and ``scripts`` in one invocation (OMN-14712). A non-existent
    root gathers zero files rather than erroring, so a repo without a
    ``scripts/`` dir still passes the same command line.
    """
    files: list[ModelSourceFile] = []
    read_errors: list[str] = []
    effect = NodeSourceFileGatherEffect()
    for root in roots:
        output = effect.handle(
            ModelSourceFileGatherInput(
                root=root, include_patterns=["**/*.py", "**/*.yaml", "**/*.yml"]
            )
        )
        root_files, root_errors = _split_gather_output(output)
        files.extend(root_files)
        read_errors.extend(root_errors)
    return files, read_errors


def _split_gather_output(
    output: ModelSourceFileGatherOutput,
) -> tuple[list[ModelSourceFile], list[str]]:
    """Separate gathered source from fatal read diagnostics."""
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
    return NodeNoHardcodedIpCheckCompute().handle(
        ModelNoHardcodedIpCheckInput(files=files)
    )


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist the canonical report through the write EFFECT node."""
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: pre-commit staged-file mode, or a full-tree walk with no args.

    Returns:
        0 on PASS, 1 on FAIL/ERROR.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-hardcoded-ip",
        description=(
            "Detect hardcoded internal IP addresses via the "
            "no-hardcoded-ip-check COMPUTE node (OMN-14659)."
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
        nargs="+",
        default=list(_DEFAULT_ROOTS),
        metavar="ROOT",
        help=(
            "One or more root directories for a full-tree walk when no "
            "filenames are given. Each root is walked independently and the "
            "eligible files are unioned. Non-existent roots gather zero files "
            f"(default: {' '.join(_DEFAULT_ROOTS)})"
        ),
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical ValidationReport JSON on PASS, FAIL and ERROR.",
    )
    parsed = parser.parse_args(argv)

    full_tree = not parsed.filenames
    if parsed.filenames:
        files, read_errors = _gather_from_filenames([Path(f) for f in parsed.filenames])
    else:
        files, read_errors = _gather_from_roots(parsed.root)

    if read_errors or (full_tree and not files):
        runtime_errors = read_errors or [
            f"zero files scanned under {' '.join(parsed.root)}: a full-tree run that scans "
            "nothing is ERROR, never PASS"
        ]
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        _write_report(parsed.report_json, error_report)
        if not read_errors:
            sys.stdout.write(f"ERROR: {runtime_errors[0]}\n")
            return 1
        print(
            f"ERROR: Failed to read {len(read_errors)} file(s):"
        )  # print-ok: CLI output
        for read_error in read_errors:
            print(f"  {read_error}")  # print-ok: CLI output
        return 1

    report = _run(files)
    _write_report(parsed.report_json, report)

    if report.overall_status == "PASS":
        print("OK: No hardcoded internal IPs found")  # print-ok: CLI output
        return 0

    print(
        f"ERROR: {report.metrics.total} hardcoded internal IP(s) found:"
    )  # print-ok: CLI output
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    print(  # print-ok: CLI output
        "\nAll endpoints must be configured via environment variables."
        "\nSuppress a justified exception with: # onex-allow-internal-ip"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
