# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for explicit filenames or a tree scan; the only module here that reads files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.cli.cli_spdx import _discover_files, _is_eligible_file
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.spdx_headers_check.model_spdx_headers_check_input import (
    ModelSpdxHeadersCheckInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_spdx_headers_check_compute.handler import (
    VALIDATOR_ID,
    NodeSpdxHeadersCheckCompute,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

# Every eligible extension plus the two exact names cli_spdx treats as eligible.
_INCLUDE_PATTERNS = [
    "**/*.py",
    "**/*.sh",
    "**/*.bash",
    "**/*.yml",
    "**/*.yaml",
    "**/*.toml",
    "**/Dockerfile",
    "**/Makefile",
]


def _select(paths: list[str]) -> list[Path]:
    """Mirror validate_files: warn on and skip missing or ineligible explicit paths."""
    selected: list[Path] = []
    for path in (Path(arg) for arg in paths):
        if path.is_file():
            if _is_eligible_file(path):
                selected.append(path)
            else:
                sys.stderr.write(f"Warning: skipping ineligible file: {path}\n")
        elif path.is_dir():
            selected.extend(_discover_files(path))
        else:
            sys.stderr.write(f"Warning: path does not exist: {path}\n")
    # Dedupe by path, then sort: the order the script validated and printed in.
    return sorted(dict.fromkeys(selected))


def _gather(paths: list[Path]) -> tuple[list[ModelSourceFile], list[str]]:
    if not paths:
        return [], []
    try:
        output = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=".",
                explicit_paths=[str(path) for path in paths],
                include_patterns=_INCLUDE_PATTERNS,
            )
        )
    except (OSError, UnicodeError) as exc:
        return [], [f"read error: {exc}"]
    errors = [f"{skipped.path}: {skipped.reason}" for skipped in output.skipped]
    return [ModelSourceFile(path=f.path, source=f.source) for f in output.files], errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Return zero only on PASS; silent on success, as the old hook was."""
    parser = argparse.ArgumentParser(
        prog="spdx-headers-check",
        description="Require the canonical SPDX header through the canonical COMPUTE node.",
    )
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root", default=".")
    parser.add_argument("--report-json", default=None)
    parsed = parser.parse_args(argv)
    full_tree = not parsed.filenames
    selected = _select(parsed.filenames or [parsed.root])
    files, errors = _gather(selected)
    if not errors and full_tree and not files:
        errors = [
            f"zero files scanned under {parsed.root}: a full-tree run that scans "
            "nothing is ERROR, never PASS"
        ]
    if errors:
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, tuple(errors))
        _write_report(parsed.report_json, report)
        for error in errors:
            sys.stdout.write(f"ERROR: {error}\n")
        return 1

    report = NodeSpdxHeadersCheckCompute().handle(
        ModelSpdxHeadersCheckInput(files=files)
    )
    _write_report(parsed.report_json, report)
    if report.overall_status == "PASS":
        return 0
    sys.stdout.write(
        f"\nSPDX Header Validation Failed — {len(report.findings)} file(s):\n\n"
    )
    for finding in report.findings:
        sys.stdout.write(f"  {finding.message}\n")
    sys.stdout.write("\nRun `onex spdx fix <path>` to fix.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
