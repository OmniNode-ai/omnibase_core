# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI preserving the old scanner's paths, flags, output and exit codes.

The old traversal includes schema files, hidden directories and files of any
size. Enumerate that same candidate set and ask the gather EFFECT to read it
in explicit mode, which avoids its different default traversal exclusions.
Report persistence belongs exclusively to the report-write EFFECT.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.handler import (
    NodeHardcodedTopicCheckCompute,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.matcher_hardcoded_topic import (
    VALIDATOR_ID,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

_TEXT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".sh",
        ".toml",
        ".txt",
        ".rst",
        ".cfg",
        ".ini",
    }
)
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        ".next",
        "dist",
        "build",
        "graphify-out",
        "dod_receipts",
        "evidence",
        ".evidence",
        ".onex_state",
    }
)


def _gather_paths(paths: list[Path]) -> tuple[list[ModelSourceFile], list[str]]:
    """Read the original CLI's candidate set through the gather EFFECT."""
    candidates: list[str] = []
    for path in paths:
        if path.is_file():
            if path.suffix in _TEXT_EXTENSIONS and not any(
                part in _SKIP_DIRS for part in path.parts
            ):
                candidates.append(str(path))
        elif path.is_dir():
            candidates.extend(
                str(child)
                for child in sorted(path.rglob("*"))
                if not any(part in _SKIP_DIRS for part in child.parts)
                and child.is_file()
                and child.suffix in _TEXT_EXTENSIONS
            )
    patterns = [f"**/*{suffix}" for suffix in sorted(_TEXT_EXTENSIONS)]
    if not candidates:
        return [], []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=candidates,
            include_patterns=patterns,
            decode_errors="replace",
        )
    )
    files = [
        ModelSourceFile(path=file.path, source=file.source) for file in output.files
    ]
    errors = [
        f"{item.path}: {item.reason}"
        for item in output.skipped
        if item.reason.startswith(("read error:", "error checking file size:"))
    ]
    return files, errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _render_report(
    report: ModelValidationReport, *, quiet: bool, report_only: bool
) -> None:
    for finding in report.findings:
        sys.stdout.write(f"{finding.message}\n")
    if quiet:
        return
    if report.findings:
        sys.stdout.write(
            f"\n{len(report.findings)} hardcoded onex.* topic literal(s). Declare the "
            "topic in contract.yaml and resolve it through the contract, or add "
            "`# " + "onex" + "-allow-topic-literal` to suppress an approved, "
            "source-of-truth declaration.\n"
        )
        if report_only:
            sys.stdout.write(
                "[report-only] not failing the run (OMN-13294 burn-down "
                "phase). Flip to blocking when findings reach zero.\n"
            )
    else:
        sys.stdout.write("No hardcoded onex.* topic-literal violations found.\n")


def main(argv: list[str] | None = None) -> int:
    """Scan files or directories, retaining report-only's unconditional success."""
    parser = argparse.ArgumentParser(
        prog="check-hardcoded-topic-compute",
        description="Detect hardcoded event-topic string literals through a canonical COMPUTE node.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        type=Path,
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--root", default=None, help="Root directory when no filenames are supplied"
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical validation report through the report-write EFFECT",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress the trailing summary line"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="Print findings but always exit 0"
    )
    parsed = parser.parse_args(argv)
    paths = parsed.filenames or [
        Path(parsed.root) if parsed.root is not None else Path()
    ]
    files, errors = _gather_paths(paths)
    scan_report = NodeHardcodedTopicCheckCompute().handle(
        ModelHardcodedTopicCheckInput(files=files)
    )

    full_tree = not parsed.filenames or any(path.is_dir() for path in paths)
    if full_tree and not files and not errors:
        errors = [f"zero files scanned under {', '.join(str(path) for path in paths)}"]
    if errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(errors)
        )
        report = ModelValidationReport.from_findings(
            findings=scan_report.findings + error_report.findings,
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
    else:
        report = scan_report
    _write_report(parsed.report_json, report)
    if errors and parsed.root is not None and not parsed.filenames:
        sys.stdout.write("ERROR: " + "\nERROR: ".join(errors) + "\n")
        return 0 if parsed.report_only else 1
    _render_report(scan_report, quiet=parsed.quiet, report_only=parsed.report_only)
    if parsed.report_only:
        return 0
    return 1 if scan_report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
