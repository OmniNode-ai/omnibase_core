# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for the core AI-slop COMPUTE node with source/report EFFECT boundaries.

    python -m omnibase_core.nodes.node_ai_slop_check_compute.runtime_ai_slop_check --strict files...

No arguments retain the script's empty-input success. ``--root`` explicitly
requests a full-tree scan and rejects an empty scan. Directory arguments scan
Python recursively and also Markdown with ``--report``, as the script does.
CI and pre-commit provide the selected paths and their existing exclusions;
the script itself has no path exclusions. Directory expansion preserves the
script's scope, including schema and hidden directories, before the gather
EFFECT reads explicit paths, bypassing that EFFECT's unrelated walk filters.

Exit codes: 1 for script ERROR or runtime failures, 2 for strict WARNING,
otherwise 0. Script INFO maps to canonical PASS with its original severity in
finding evidence. The script has no PASS line, failure header or fix hint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_ai_slop_check_compute.handler import (
    NodeAiSlopCheckCompute,
)
from omnibase_core.nodes.node_ai_slop_check_compute.matcher_ai_slop import VALIDATOR_ID
from omnibase_core.nodes.node_ai_slop_check_compute.rules_ai_slop import (
    resolve_script_rules,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _expand_paths(filenames: list[str], *, report: bool) -> list[str]:
    paths: list[str] = []
    for raw in filenames:
        path = Path(raw)
        if path.is_dir():
            paths.extend(str(p) for p in path.rglob("*.py"))
            if report:
                paths.extend(str(p) for p in path.rglob("*.md"))
        elif path.exists():
            paths.append(str(path))
    return [path for path in paths if Path(path).suffix in (".py", ".md")]


def main(argv: list[str] | None = None) -> int:
    """Run core's CLI semantics through canonical gather, compute and write."""
    parser = argparse.ArgumentParser(
        description="Check Python/Markdown files for AI-slop patterns."
    )
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root", default=None)
    parser.add_argument("--report-json", default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--config", metavar="REPO_ROOT", default=None)
    args = parser.parse_args(argv)
    full_tree = not args.filenames and args.root is not None
    paths = _expand_paths(
        [args.root] if full_tree else args.filenames, report=args.report
    )
    files: list[ModelSourceFile] = []
    errors: dict[str, str] = {}
    if paths:
        gathered = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=".", explicit_paths=paths, include_patterns=["**/*.py", "**/*.md"]
            )
        )
        files = [ModelSourceFile(path=f.path, source=f.source) for f in gathered.files]
        errors = {
            s.path: f"Cannot read file: {s.reason.split(': ', 1)[-1]}"
            for s in gathered.skipped
            if s.reason.startswith(("read error:", "error checking file size:"))
        }
    if full_tree and not files and not errors:
        messages = (
            f"zero files scanned under {args.root}: a full-tree run that scans nothing is ERROR, never PASS",
        )
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, messages)
        _write_report(args.report_json, report)
        sys.stderr.write(f"ERROR: {messages[0]}\n")
        return 1

    root = Path(args.config) if args.config else Path.cwd()
    rules = resolve_script_rules(root, docstrings=True) + resolve_script_rules(
        root, docstrings=False
    )
    fallback = resolve_script_rules(Path.cwd(), docstrings=True)
    request = ModelAiSlopCheckInput(
        files=files,
        rules=rules,
        fallback_docstring_rules=fallback,
        strict=args.strict,
        report=args.report,
    )
    if errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(errors.values())
        )
        error_findings = {
            path: finding.model_copy(
                update={
                    "location": f"{path}:0",
                    "rule_id": "file_read",
                    "evidence": {"script_severity": "ERROR"},
                }
            )
            for path, finding in zip(errors, error_report.findings, strict=True)
        }
        sources = {file.path: file for file in files}
        findings: list[ModelValidationFindingEmbed] = []
        for path in paths:
            if path in error_findings:
                findings.append(error_findings[path])
            elif path in sources:
                findings.extend(
                    NodeAiSlopCheckCompute()
                    .handle(request.model_copy(update={"files": [sources[path]]}))
                    .findings
                )
        report = ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(
                profile="strict" if args.strict else "default"
            ),
            validators_run=(VALIDATOR_ID,),
        )
    else:
        report = NodeAiSlopCheckCompute().handle(request)
    _write_report(args.report_json, report)
    rows: list[dict[str, str | int]] = []
    for finding in report.findings:
        path, line = (finding.location or ":0").rsplit(":", 1)
        severity = str(finding.evidence["script_severity"])
        rows.append(
            {
                "filename": path,
                "line": int(line),
                "check": str(finding.rule_id),
                "severity": severity,
                "message": finding.message,
            }
        )
        if not args.json_output:
            sys.stderr.write(
                f"{finding.location}: [{severity}] {finding.rule_id}: {finding.message}\n"
            )
    if args.json_output:
        sys.stdout.write(json.dumps(rows, indent=2) + "\n")
    if any(f.evidence["script_severity"] == "ERROR" for f in report.findings):
        return 1
    if args.strict and any(
        f.evidence["script_severity"] == "WARNING" for f in report.findings
    ):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
