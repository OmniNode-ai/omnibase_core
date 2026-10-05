# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI adapter: all source reads and report writes go through EFFECT nodes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_interpreter_check_input import (
    ModelPrecommitInterpreterCheckInput,
)
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
from omnibase_core.nodes.node_precommit_interpreter_check_compute.handler import (
    NodePrecommitInterpreterCheckCompute,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.matcher_precommit_interpreter import (
    SUPPRESS_MARKER,
    VALIDATOR_ID,
    eligible_entries,
    referenced_scripts,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


def _gather(
    paths: list[Path], root: Path, missing_is_error: bool
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read explicitly selected config or referenced shell paths via EFFECT."""
    try:
        output = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=str(root),
                explicit_paths=[str(path) for path in paths],
                include_patterns=["*"],
            )
        )
    except (OSError, UnicodeError) as exc:
        return [], [f"ERROR: failed to read source: {exc}"]
    errors = [
        f"{item.path}: {item.reason}"
        for item in output.skipped
        if item.reason.startswith(("read error:", "error checking file size:"))
    ]
    if missing_is_error:
        errors.extend(
            f"ERROR: {item.path} not found"
            for item in output.skipped
            if item.reason == "not a file"
        )
    files = []
    for file in output.files:
        path = Path(file.path)
        label = (
            path.relative_to(root).as_posix()
            if path.is_relative_to(root)
            else str(path)
        )
        files.append(ModelSourceFile(path=label, source=file.source))
    return files, errors


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist only through the paired report-write EFFECT."""
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _display(
    report: ModelValidationReport, request: ModelPrecommitInterpreterCheckInput
) -> None:
    """Reproduce the script's stdout, stderr, header, and remediation."""
    if any(
        finding.rule_id in {"non-vacuity", "invalid-config"}
        for finding in report.findings
    ):
        for finding in report.findings:
            sys.stderr.write(f"{finding.message}\n")
        return
    if report.findings:
        sys.stderr.write("Bare-interpreter pre-commit hooks found:\n")
        for finding in report.findings:
            sys.stderr.write(f"  - {finding.message}\n")
        sys.stderr.write(
            "\nFix: replace the bare interpreter with the repo's sanctioned form, "
            "`uv run python <script>`.\n"
            f"Suppress a reviewed false positive with `# {SUPPRESS_MARKER}: <reason>`.\n"
        )
        return
    entries = eligible_entries(request.config.source)
    supplied = {file.path for file in request.scripts}
    scripts = {
        path
        for _, entry, _ in entries
        for path in referenced_scripts(entry, request.repository_root)
        if path in supplied
    }
    sys.stdout.write(
        f"OK: {len(entries)} local pre-commit hooks and {len(scripts)} "
        "referenced shell scripts use a resolvable interpreter\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Check named configs, or the root config when filenames are omitted."""
    parser = argparse.ArgumentParser(prog="check-precommit-interpreter")
    parser.add_argument(
        "filenames", nargs="*", help="Pre-commit config paths to check."
    )
    parser.add_argument(
        "--root", default=".", help="Repository root for referenced shell scripts."
    )
    parser.add_argument(
        "--report-json", default=None, help="Write a canonical validation report."
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    paths = [Path(filename).resolve() for filename in args.filenames] or [
        root / ".pre-commit-config.yaml"
    ]
    configs, errors = _gather(paths, root, missing_is_error=True)
    requests = []
    for config in configs:
        try:
            entries = eligible_entries(config.source)
        except (yaml.YAMLError, ModelOnexError):
            entries = []
        script_paths = list(
            dict.fromkeys(
                root / path
                for _, entry, _ in entries
                for path in referenced_scripts(entry)
            )
        )
        if script_paths:
            scripts, script_errors = _gather(script_paths, root, missing_is_error=False)
            errors.extend(script_errors)
        else:
            scripts = []
        requests.append(
            ModelPrecommitInterpreterCheckInput(
                config=config, scripts=scripts, repository_root=str(root)
            )
        )
    if errors or not configs:
        diagnostics = errors or [f"ERROR: {root / '.pre-commit-config.yaml'} not found"]
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(diagnostics)
        )
        _write_report(args.report_json, report)
        for diagnostic in diagnostics:
            sys.stderr.write(f"{diagnostic}\n")
        return 1
    reports = [
        NodePrecommitInterpreterCheckCompute().handle(request) for request in requests
    ]
    report = ModelValidationReport.from_findings(
        findings=tuple(finding for result in reports for finding in result.findings),
        request=ModelValidationRequestRef(profile="default"),
        validators_run=(VALIDATOR_ID,),
    )
    _write_report(args.report_json, report)
    for result, request in zip(reports, requests, strict=True):
        _display(result, request)
    return 0 if report.overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
