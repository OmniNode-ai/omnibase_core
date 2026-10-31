# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-raw-sqlite3 check — pre-commit hook + CI entrypoint.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoRawSqlite3CheckCompute``) — DRY per the OMN-13305 pattern, following
the ``node_no_utcnow_check_compute`` template (OMN-14656): a single module
owns the pure handler plus a synchronous CLI ``main()`` that performs all
filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): the staged files pre-commit hands us
  are read through the gather EFFECT node — no directory walk needed.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks
  ``--root`` (default ``src``) via the paired ``node_source_file_gather_effect``
  EFFECT node, reproducing the oracle CI gate's tree scan
  (``omniclaude/scripts/validation/validate_no_raw_sqlite3.py``
  ``root.rglob("*.py")``). The oracle additionally restricts the walk to
  ``src/omniclaude`` and ``plugins/onex`` and excludes ``tests/`` — those are
  omniclaude-specific root-scoping choices, generalized here to a plain
  ``--root`` (default ``src``) since this node ships as a cross-repo remote
  pre-commit hook.

Usage::

    python -m omnibase_core.nodes.node_no_raw_sqlite3_check_compute.runtime_no_raw_sqlite3_check file1.py file2.py
    python -m omnibase_core.nodes.node_no_raw_sqlite3_check_compute.runtime_no_raw_sqlite3_check
    python -m omnibase_core.nodes.node_no_raw_sqlite3_check_compute.runtime_no_raw_sqlite3_check --root src

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

import argparse
import sys
from functools import cache
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.no_raw_sqlite3_check.model_no_raw_sqlite3_check_input import (
    ModelNoRawSqlite3CheckInput,
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
from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.handler import (
    NodeNoRawSqlite3CheckCompute,
)
from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.visitor_raw_sqlite3 import (
    VALIDATOR_ID,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

__all__ = ["main"]

_DEFAULT_ROOT: Final[str] = "src"


@cache
def _container() -> ModelONEXContainer:
    """Bind this runtime's effects and COMPUTE node in a container, built once."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for implementation in (
        NodeNoRawSqlite3CheckCompute,
        NodeSourceFileGatherEffect,
        NodeValidationReportWriteEffect,
    ):
        run_coro_sync(
            registry.register_service(
                implementation,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Non-``.py`` and missing paths are intentionally skipped. Read errors on
    existing Python files are returned as fatal diagnostics so the runtime
    does not report PASS with unscanned source.
    """
    output = (
        _container()
        .get_service(NodeSourceFileGatherEffect)
        .handle(
            ModelSourceFileGatherInput(
                root=".",
                explicit_paths=[str(path) for path in paths],
                include_patterns=["**/*.py"],
            )
        )
    )
    return _split_gather_output(output)


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only filesystem walk in this module —
    delegated to the paired canonical node rather than re-implemented here.
    """
    output = (
        _container()
        .get_service(NodeSourceFileGatherEffect)
        .handle(ModelSourceFileGatherInput(root=root, include_patterns=["**/*.py"]))
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
    return (
        _container()
        .get_service(NodeNoRawSqlite3CheckCompute)
        .handle(ModelNoRawSqlite3CheckInput(files=files))
    )


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist the canonical report through the write EFFECT node."""
    if path is not None:
        _container().get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: pre-commit staged-file mode, or a full-tree walk with no args.

    Returns:
        0 on PASS, 1 on FAIL/ERROR.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-raw-sqlite3",
        description=(
            "Detect raw sqlite3.connect() calls outside adapter definitions via "
            "the no-raw-sqlite3-check COMPUTE node (OMN-14659)."
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
            f"ERROR: Failed to read {len(read_errors)} Python file(s):"
        )  # print-ok: CLI output
        for read_error in read_errors:
            print(f"  {read_error}")  # print-ok: CLI output
        return 1

    report = _run(files)
    _write_report(parsed.report_json, report)

    if report.overall_status == "PASS":
        print(  # print-ok: CLI output
            "OK: No raw sqlite3.connect() calls found outside adapter definitions"
        )
        return 0

    print(  # print-ok: CLI output
        f"FAIL: Found {report.metrics.total} raw sqlite3.connect() call(s) "
        "outside adapter definitions:"
    )
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    print(  # print-ok: CLI output
        "\nOnly *_adapter.py files may call sqlite3.connect() directly."
        "\nOther code must receive a database adapter via DI injection."
        "\nAdd '# di-ok' to suppress for legitimate adapter bootstrap."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
