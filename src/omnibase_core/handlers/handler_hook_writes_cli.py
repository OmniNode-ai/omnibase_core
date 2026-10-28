# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the hook-writes check (OMN-21433, plan task T2.6).

Overlay loading, hook file discovery and reads, and report writes happen here.
The verdict is the pure ``HandlerHookWrites``. Exit codes: 0 for PASS, 1 for
FAIL or ERROR, including scans that read zero hooks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_hook_writes import HandlerHookWrites
from omnibase_core.handlers.handler_hook_writes_rules import VALIDATOR_ID, parse_hooks
from omnibase_core.models.hook_writes.model_hook_writes_check_input import (
    ModelHookWritesCheckInput,
)
from omnibase_core.models.hook_writes.model_hook_writes_overlay import (
    ModelHookWritesOverlay,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

__all__ = ["DEFAULT_OVERLAY", "main"]

DEFAULT_OVERLAY: Final[str] = ".hook-writes-overlay.yaml"


def gather(
    root: Path, filenames: list[str]
) -> tuple[list[ModelSourceFile], int, list[str]]:
    """Read and validate hook files, retaining their order and counting hooks."""
    relative = filenames or [
        name
        for name in (".pre-commit-config.yaml", ".pre-commit-hooks.yaml")
        if (root / name).exists()
    ]
    if not relative:
        return [], 0, [f"no hook file found under {root}"]

    files: list[ModelSourceFile] = []
    hooks_scanned = 0
    errors: list[str] = []
    for filename in relative:
        try:
            source = (root / filename).read_text(encoding="utf-8")
            hooks_scanned += len(parse_hooks(filename, source))
            files.append(ModelSourceFile(path=filename, source=source))
        except (OSError, ValueError, ModelOnexError) as exc:
            errors.append(f"{filename}: cannot read or parse hook file: {exc}")
    return files, hooks_scanned, errors


def _out(line: str) -> None:
    """Write one CLI message to standard output."""
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist a requested report through the report-writing EFFECT node."""
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _runtime_failure(errors: list[str], report_path: str | None) -> int:
    """Report runtime errors without allowing an incomplete scan to pass."""
    report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, tuple(errors))
    _write_report(report_path, report)
    for message in errors:
        _out(f"ERROR: {message}")
    _out("ERROR: hook-writes check could not complete")
    return 1


def main(argv: list[str] | None = None) -> int:
    """Check supplied or discovered hook files; return 0 on PASS, 1 on FAIL/ERROR."""
    parser = argparse.ArgumentParser(
        prog="check-hook-writes",
        description="Require pre-commit hooks to check without rewriting (OMN-21433).",
    )
    parser.add_argument("filenames", nargs="*", help="Repository-relative hook files.")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--overlay",
        default=DEFAULT_OVERLAY,
        help=f"Overlay path relative to --root (default: {DEFAULT_OVERLAY})",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        metavar="PATH",
        help="Write the report JSON here.",
    )
    parsed = parser.parse_args(argv)

    try:
        root = Path(parsed.root).resolve()
        overlay = load_and_validate_yaml_model(
            root / parsed.overlay, ModelHookWritesOverlay
        )
    except (OSError, ValueError, ModelOnexError) as exc:
        return _runtime_failure(
            [f"cannot load overlay {parsed.overlay!r}: {exc}"], parsed.report_json
        )

    try:
        files, hooks_scanned, runtime_errors = gather(root, parsed.filenames)
    except (OSError, ValueError, ModelOnexError) as exc:
        return _runtime_failure(
            [f"cannot scan hook files under {root}: {exc}"], parsed.report_json
        )
    if not runtime_errors and hooks_scanned == 0:
        runtime_errors.append(
            f"zero hooks under {root}: a scan that reads nothing is ERROR, never PASS"
        )
    if runtime_errors:
        return _runtime_failure(runtime_errors, parsed.report_json)

    report = HandlerHookWrites().handle(
        ModelHookWritesCheckInput(overlay=overlay, files=tuple(files))
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status == "PASS":
        _out(f"OK: hook-writes check passed ({hooks_scanned} hooks scanned)")
        return 0
    _out(f"{report.overall_status}: hook-writes check failed; see findings above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
