# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shared fixture and report normalization for local-path parity tests."""

from __future__ import annotations

import json
from pathlib import Path

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

REPO = Path(__file__).resolve().parents[4]
FIXTURES = REPO / "tests/fixtures/validator_parity/local_paths"


def corpus() -> dict[str, str]:
    loaded: dict[str, str] = json.loads((FIXTURES / "corpus.json").read_text())
    return loaded


def report_rows(report: ModelValidationReport) -> list[tuple[str, int, str, str]]:
    rows = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        assert finding.rule_id is not None
        rows.append((path, int(line), finding.rule_id, finding.message))
    return rows


def materialize(root: Path) -> list[Path]:
    paths = []
    for name, source in corpus().items():
        path = root / f"{name}.txt"
        path.write_text(source, encoding="utf-8")
        paths.append(path)
    return paths
