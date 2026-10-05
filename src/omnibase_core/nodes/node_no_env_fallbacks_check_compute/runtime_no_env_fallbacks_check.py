# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-env-fallbacks check — pre-commit hook + CI entrypoint.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoEnvFallbacksCheckCompute``) — DRY per the OMN-13305 pattern,
following the ``node_no_utcnow_check_compute`` template (OMN-14656): a single
module owns the pure handler plus a synchronous CLI ``main()`` that performs
all filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): the staged files pre-commit hands us
  are read through the gather EFFECT node — no directory walk needed.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks
  ``--root`` (default ``src``) via the paired ``node_source_file_gather_effect``
  EFFECT node for ``*.py``/``*.sh``/``*.bash`` files, reproducing the oracle
  CI gate's file-type scope
  (``omniclaude/scripts/validate_no_env_fallbacks.py``).

  The oracle additionally scans ``scripts/`` as a separate top-level root
  (this repo's ``ModelSourceFileGatherInput`` walks a single ``root``); pass
  ``--root`` explicitly for a non-``src`` scan when porting this entrypoint
  into another repo's CI.

Usage::

    python -m omnibase_core.nodes.node_no_env_fallbacks_check_compute.runtime_no_env_fallbacks_check file1.py file2.sh
    python -m omnibase_core.nodes.node_no_env_fallbacks_check_compute.runtime_no_env_fallbacks_check
    python -m omnibase_core.nodes.node_no_env_fallbacks_check_compute.runtime_no_env_fallbacks_check --root src

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_env_fallbacks_check.model_no_env_fallbacks_check_input import (
    ModelNoEnvFallbacksCheckInput,
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
from omnibase_core.nodes.node_no_env_fallbacks_check_compute.handler import (
    NodeNoEnvFallbacksCheckCompute,
)
from omnibase_core.nodes.node_no_env_fallbacks_check_compute.matcher_env_fallbacks import (
    VALIDATOR_ID,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["main"]

_DEFAULT_ROOT: Final[str] = "src"


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Non-Python/shell and missing paths are intentionally skipped. Read
    errors on existing eligible files are returned as fatal diagnostics so
    the runtime does not report PASS with unscanned source.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=[str(path) for path in paths],
            include_patterns=["**/*.py", "**/*.sh", "**/*.bash"],
        )
    )
    return _split_gather_output(output)


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only filesystem walk in this module —
    delegated to the paired canonical node rather than re-implemented here.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=root, include_patterns=["**/*.py", "**/*.sh", "**/*.bash"]
        )
    )
    return _split_gather_output(output)


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
    return NodeNoEnvFallbacksCheckCompute().handle(
        ModelNoEnvFallbacksCheckInput(files=files)
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
        prog="check-no-env-fallbacks",
        description=(
            "Detect localhost/hardcoded-endpoint fallback defaults via the "
            "no-env-fallbacks-check COMPUTE node (OMN-14659)."
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
        files, read_errors = _gather_from_root(parsed.root)

    if read_errors or (full_tree and not files):
        runtime_errors = read_errors or [
            f"zero files scanned under {parsed.root}: a full-tree run that scans "
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
        print(  # print-ok: CLI output
            "PASS: No localhost/hardcoded-endpoint fallbacks found."
        )
        return 0

    print(  # print-ok: CLI output
        f"FAIL: {report.metrics.total} localhost/hardcoded-endpoint fallback(s) found:"
    )
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    print(  # print-ok: CLI output
        '\nFix: Replace with os.environ["VAR"] (fail-fast, no default) or raise explicitly.'
        "\nAnnotate justified exceptions with  # fallback-ok: <reason>  on the same line."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
