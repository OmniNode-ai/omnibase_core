# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI with the old local-paths output and source/report EFFECT boundaries.

Empty scans and unreadable files retain the old runtime's exit-code semantics,
while producing canonical ERROR diagnostics in the optional JSON report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.local_paths_check.model_local_paths_check_input import (
    ModelLocalPathsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
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
from omnibase_core.nodes.node_local_paths_check_compute.handler import (
    NodeLocalPathsCheckCompute,
)
from omnibase_core.nodes.node_local_paths_check_compute.matcher_local_paths import (
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
_INCLUDE_PATTERNS: Final[tuple[str, ...]] = tuple(
    f"**/*{extension}" for extension in sorted(_TEXT_EXTENSIONS)
)


def _eligible(path: str) -> bool:
    candidate = Path(path)
    return candidate.suffix in _TEXT_EXTENSIONS and not any(
        part in _SKIP_DIRS for part in candidate.parts
    )


def _split_gather_output(
    output: ModelSourceFileGatherOutput,
) -> tuple[list[ModelSourceFile], list[str]]:
    files = [
        ModelSourceFile(path=f.path, source=f.source)
        for f in output.files
        if _eligible(f.path)
    ]
    errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if _eligible(skipped.path)
        and skipped.reason.startswith(("read error:", "error checking file size:"))
    ]
    return files, errors


def _gather_paths(paths: list[Path]) -> tuple[list[ModelSourceFile], list[str]]:
    """Gather mixed file/directory arguments with the old extension and skip sets.

    The shared effect's root walk additionally excludes schemas, cache folders
    and ignore-file matches. Its skip records provide those candidate names;
    explicit gathering restores all candidates eligible under this validator's
    narrower skip policy, without performing reads outside the effect node.
    """
    files: list[ModelSourceFile] = []
    errors: list[str] = []
    gather = NodeSourceFileGatherEffect()
    for path in paths:
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir():
            output = gather.handle(
                ModelSourceFileGatherInput(
                    root=str(path),
                    include_patterns=list(_INCLUDE_PATTERNS),
                    exclude_patterns=[
                        f"{directory}/" for directory in sorted(_SKIP_DIRS)
                    ],
                    max_file_size=0,
                    decode_errors="replace",
                )
            )
            gathered, read_errors = _split_gather_output(output)
            restore = [
                skipped.path
                for skipped in output.skipped
                if _eligible(skipped.path)
                and skipped.reason in {"schema file", "ignored by pattern"}
            ]
            if restore:
                recovered, recovery_errors = _split_gather_output(
                    gather.handle(
                        ModelSourceFileGatherInput(
                            root=str(path),
                            explicit_paths=restore,
                            include_patterns=list(_INCLUDE_PATTERNS),
                            decode_errors="replace",
                        )
                    )
                )
                gathered.extend(recovered)
                read_errors.extend(recovery_errors)
            gathered.sort(key=lambda file: Path(file.path))
        elif _eligible(str(path)):
            gathered, read_errors = _split_gather_output(
                gather.handle(
                    ModelSourceFileGatherInput(
                        root=".",
                        explicit_paths=[str(path)],
                        include_patterns=list(_INCLUDE_PATTERNS),
                        decode_errors="replace",
                    )
                )
            )
        else:
            continue
        files.extend(gathered)
        errors.extend(read_errors)
    return files, errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist reports exclusively through the canonical write effect."""
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Scan positional files/directories or --root, preserving old CLI output."""
    parser = argparse.ArgumentParser(
        prog="check-local-paths-compute",
        description="Detect machine-specific absolute paths via a pure COMPUTE node.",
    )
    parser.add_argument("filenames", nargs="*", help="Files or directories to check")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-violation context lines and the summary",
    )
    parser.add_argument(
        "--root", default=".", help="Root for scans without positional paths"
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the canonical validation report"
    )
    parsed = parser.parse_args(argv)
    paths = (
        [Path(p) for p in parsed.filenames] if parsed.filenames else [Path(parsed.root)]
    )
    files, runtime_errors = _gather_paths(paths)
    scan_report = NodeLocalPathsCheckCompute().handle(
        ModelLocalPathsCheckInput(files=files)
    )
    if (
        not files
        and not runtime_errors
        and (not parsed.filenames or any(path.is_dir() for path in paths))
    ):
        runtime_errors = [
            f"zero files scanned under {', '.join(str(p) for p in paths)}"
        ]
    report = scan_report
    if runtime_errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        report = ModelValidationReport.from_findings(
            findings=(*scan_report.findings, *error_report.findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
    _write_report(parsed.report_json, report)
    for finding in scan_report.findings:
        sys.stdout.write(f"{finding.message}\n")
        if not parsed.quiet:
            sys.stdout.write(f"  {finding.evidence['context']}\n")
    total_findings = len(scan_report.findings)
    if not parsed.quiet:
        if total_findings:
            sys.stdout.write(
                f"\n{total_findings} local path violation(s). Remove hardcoded "
                f"paths or add `# {SUPPRESSION_MARKER}` to suppress.\n"
            )
        else:
            sys.stdout.write("No local path violations found.\n")
    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
