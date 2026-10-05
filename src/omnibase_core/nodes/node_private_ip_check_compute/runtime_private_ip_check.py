# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI preserving the original private-IP runtime's scope and console output.

Reads and report writes belong to the canonical EFFECT nodes. The original
runtime returns zero for unreadable inputs and empty trees; this CLI preserves
those exit codes while recording the incomplete scan as an ERROR report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.private_ip_check.model_private_ip_check_input import (
    ModelPrivateIpCheckInput,
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
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_private_ip_check_compute.handler import (
    NodePrivateIpCheckCompute,
)
from omnibase_core.nodes.node_private_ip_check_compute.matcher_private_ip import (
    SUPPRESSION_MARKER,
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


def _eligible(path: Path) -> bool:
    return path.suffix in _TEXT_EXTENSIONS and not any(
        part in _SKIP_DIRS for part in path.parts
    )


def _split_output(
    output: ModelSourceFileGatherOutput,
) -> tuple[list[ModelSourceFile], list[str]]:
    files = [
        ModelSourceFile(path=file.path, source=file.source)
        for file in output.files
        if _eligible(Path(file.path))
    ]
    errors = [
        f"{item.path}: {item.reason}"
        for item in output.skipped
        if _eligible(Path(item.path))
        and item.reason.startswith(("read error:", "error checking file size:"))
    ]
    return files, errors


def _gather_explicit(
    effect: NodeSourceFileGatherEffect, paths: list[str], patterns: list[str]
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read through the effect and preserve the old UTF-8 replacement policy."""
    output = effect.handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=paths,
            include_patterns=patterns,
            decode_errors="replace",
        )
    )
    return _split_output(output)


def _gather_paths(paths: list[Path]) -> tuple[list[ModelSourceFile], list[str]]:
    """Gather old-runtime scopes, recovering generic gather-only exclusions."""
    files: list[ModelSourceFile] = []
    errors: list[str] = []
    effect = NodeSourceFileGatherEffect()
    patterns = [f"**/*{suffix}" for suffix in sorted(_TEXT_EXTENSIONS)]
    for path in paths:
        if path.is_file() and _eligible(path):
            gathered, read_errors = _gather_explicit(effect, [str(path)], patterns)
        elif path.is_dir():
            request = ModelSourceFileGatherInput(
                root=str(path),
                include_patterns=patterns,
                max_file_size=0,
                decode_errors="replace",
                exclude_patterns=[f"{directory}/" for directory in sorted(_SKIP_DIRS)],
            )
            output = effect.handle(request)
            gathered, read_errors = _split_output(output)
            recovery_paths = [
                item.path
                for item in output.skipped
                if _eligible(Path(item.path))
                and item.reason in {"ignored by pattern", "schema file"}
            ]
            if recovery_paths:
                recovered, recovery_errors = _gather_explicit(
                    effect, recovery_paths, patterns
                )
                gathered.extend(recovered)
                read_errors.extend(recovery_errors)
        else:
            continue
        files.extend(sorted(gathered, key=lambda file: file.path))
        errors.extend(read_errors)
    return files, errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Scan filenames or directories; preserve quiet and original exit codes."""
    parser = argparse.ArgumentParser(
        prog="check-private-ip-compute",
        description="Detect hardcoded RFC1918 private-IP literals via the canonical COMPUTE node.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        type=Path,
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-violation context lines and the summary",
    )
    parser.add_argument(
        "--root",
        nargs="+",
        default=["."],
        help="Root directories when filenames are omitted",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical report on PASS, FAIL, and ERROR",
    )
    parsed = parser.parse_args(argv)
    paths = parsed.filenames or [Path(root) for root in parsed.root]
    files, errors = _gather_paths(paths)
    report = NodePrivateIpCheckCompute().handle(ModelPrivateIpCheckInput(files=files))
    if (
        not files
        and not errors
        and (not parsed.filenames or any(path.is_dir() for path in paths))
    ):
        errors.append(
            "zero files scanned under " + " ".join(str(path) for path in paths)
        )
    if errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(errors)
        )
        persisted = ModelValidationReport.from_findings(
            findings=report.findings + error_report.findings,
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
    else:
        persisted = report
    _write_report(parsed.report_json, persisted)
    for finding in report.findings:
        sys.stdout.write(f"{finding.message}\n")
        if not parsed.quiet:
            sys.stdout.write(f"  {finding.evidence['context']}\n")
    total = report.metrics.total
    if not parsed.quiet:
        if total:
            sys.stdout.write(
                f"\n{total} hardcoded private-IP violation(s). Resolve the "
                "endpoint from the routing authority / contract, or add "
                f"`# {SUPPRESSION_MARKER}` to suppress an approved fixture.\n"
            )
        else:
            sys.stdout.write("No hardcoded private-IP violations found.\n")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
