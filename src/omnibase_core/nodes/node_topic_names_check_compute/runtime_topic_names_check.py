# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Legacy repo-root CLI plus filenames and fail-closed --root report modes.

Legacy directory invocations preserve zero-file PASS and silent unreadable-file
skips. New --root/filenames modes surface those conditions as runtime ERRORs.
All source reads and report writes go through the canonical EFFECT nodes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.topic_names_check.model_topic_names_check_input import (
    ModelTopicNamesCheckInput,
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
from omnibase_core.nodes.node_topic_names_check_compute.handler import (
    NodeTopicNamesCheckCompute,
)
from omnibase_core.nodes.node_topic_names_check_compute.matcher_topic_names import (
    VALIDATOR_ID,
    extract_topics,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

_GLOBS = ("**/*topic*.py", "**/*topics*.py", "**/*topic*.ts", "**/*topics*.ts")


def _gather(paths: list[Path]) -> tuple[list[ModelSourceFile], list[str]]:
    """Read exact oracle candidates, retaining hidden/schema paths and no cap."""
    if not paths:
        return [], []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=[str(path) for path in paths],
            include_patterns=["**/*"],
        )
    )
    return (
        [ModelSourceFile(path=file.path, source=file.source) for file in output.files],
        [f"{file.path}: {file.reason}" for file in output.skipped],
    )


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Return the core CLI's 0/1/2 codes; support explicit effect-backed scans."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("Usage: onex-validate-topics <repo-root> [--verbose]\n")
        return 2
    parser = argparse.ArgumentParser(prog="onex-validate-topics", add_help=False)
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root")
    parser.add_argument("--report-json")
    parser.add_argument("--verbose", action="store_true")
    parsed, _unknown = parser.parse_known_args(args)
    legacy = parsed.root is None and (
        (
            bool(parsed.filenames)
            and (
                Path(parsed.filenames[0]).is_dir()
                or Path(parsed.filenames[0]).suffix.lower() not in {".py", ".ts"}
            )
        )
        or (parsed.report_json is None and args[0].startswith("-"))
    )
    full_tree = parsed.root is not None or legacy
    root = Path(parsed.root or (args[0] if legacy else ".")).resolve()
    if full_tree and not root.is_dir():
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, (f"Error: {root} is not a directory",)
        )
        _write_report(parsed.report_json, report)
        sys.stderr.write(f"Error: {root} is not a directory\n")
        return 2
    paths = (
        sorted({path for pattern in _GLOBS for path in root.glob(pattern)})
        if full_tree
        else [Path(path) for path in parsed.filenames]
    )
    files, errors = _gather(paths)
    if not legacy and (errors or (full_tree and not files)):
        diagnostics = tuple(errors) or (f"zero files scanned under {root}",)
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, diagnostics)
        _write_report(parsed.report_json, report)
        for diagnostic in diagnostics:
            sys.stdout.write(f"ERROR: {diagnostic}\n")
        return 1
    if full_tree:
        files = [
            ModelSourceFile(
                path=str(Path(file.path).relative_to(root)), source=file.source
            )
            for file in files
        ]
    report = NodeTopicNamesCheckCompute().handle(ModelTopicNamesCheckInput(files=files))
    _write_report(parsed.report_json, report)
    total_topics = sum(len(extract_topics(file.path, file.source)) for file in files)
    if parsed.verbose:
        sys.stdout.write(
            f"Scanned {len(paths)} files, found {total_topics} topic constants\n"
        )
    if report.overall_status == "PASS":
        sys.stdout.write(
            f"OK: {total_topics} topic(s) validated across {len(paths)} file(s)\n"
        )
        return 0
    sys.stdout.write(f"FAIL: {len(report.findings)} violation(s) found:\n\n")
    for finding in report.findings:
        sys.stdout.write(f"  {finding.location}: {finding.message}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
