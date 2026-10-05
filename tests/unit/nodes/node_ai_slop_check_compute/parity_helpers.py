# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared fixture and oracle normalization for AI-slop parity."""

from __future__ import annotations

import json
from pathlib import Path

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_ai_slop_check_compute.handler import (
    NodeAiSlopCheckCompute,
)
from omnibase_core.nodes.node_ai_slop_check_compute.rules_ai_slop import (
    resolve_script_rules,
)
from omnibase_core.nodes.node_ai_slop_check_compute.runtime_ai_slop_check import main

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "tests/fixtures/validator_parity/ai_slop"
CORPUS: dict[str, str] = json.loads((FIXTURES / "corpus.json").read_text())
GOLDEN = json.loads((FIXTURES / "golden.json").read_text())


def rows_parity(report: ModelValidationReport) -> list[dict[str, str | int]]:
    rows = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        rows.append(
            {
                "filename": path,
                "line": int(line),
                "check": finding.rule_id,
                "severity": finding.evidence["script_severity"],
                "message": finding.message,
            }
        )
    return rows


def handler_parity(
    paths: list[Path], strict: bool, report: bool, config: Path | None = None
) -> ModelValidationReport:
    return NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[
                ModelSourceFile(path=str(p), source=p.read_text())
                for p in paths
                if p.suffix in (".py", ".md")
            ],
            strict=strict,
            report=report,
            rules=resolve_script_rules(config or ROOT, docstrings=True)
            + resolve_script_rules(config or ROOT, docstrings=False),
            fallback_docstring_rules=resolve_script_rules(ROOT, docstrings=True),
        )
    )


def runtime_parity(
    paths: list[Path],
    strict: bool,
    report: bool,
    output: Path,
    extra: list[str] | None = None,
) -> tuple[int, ModelValidationReport]:
    args = ["--report-json", str(output)]
    if strict:
        args.append("--strict")
    if report:
        args.append("--report")
    code = main([*args, *(extra or []), *map(str, paths)])
    return code, ModelValidationReport.model_validate_json(output.read_text())


def normalized_parity(
    rows: list[dict[str, str | int]],
) -> list[tuple[str, int, str, str, str]]:
    return sorted(
        (
            str(r["filename"]),
            int(r["line"]),
            str(r["check"]),
            str(r["severity"]),
            str(r["message"]),
        )
        for r in rows
    )


def tree_paths_parity() -> list[Path]:
    return sorted((ROOT / "src").rglob("*.py"))
