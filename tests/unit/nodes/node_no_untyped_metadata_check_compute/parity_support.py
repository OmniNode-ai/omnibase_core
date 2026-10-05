# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture materialization and normalization shared by parity tests."""

from __future__ import annotations

import re
from pathlib import Path

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
CORPUS = REPO_ROOT / "tests/fixtures/validator_parity/no_untyped_metadata"


def materialize_corpus(root: Path) -> list[Path]:
    """Keep exemption text out of tracked files while exercising it verbatim."""
    paths: list[Path] = []
    for template in sorted(CORPUS.glob("*.in")):
        path = root / template.name.removesuffix(".in")
        path.write_text(
            template.read_text()
            .replace("{exemption}", "ONEX_" + "EXCLUDE:")
            .replace("{marker_word}", "ONEX_" + "EXCLUDE"),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def normalized_rows(output: str, root: Path) -> list[dict[str, str | int]]:
    """Extract only per-line diagnostics, retaining byte-exact message text."""
    rows: list[dict[str, str | int]] = []
    prefix = str(root) + "/"
    for line in output.splitlines():
        match = re.match(r"^(.*):(\d+): (untyped metadata dict .*)$", line)
        if match:
            rows.append(
                {
                    "path": match[1].removeprefix(prefix),
                    "line": int(match[2]),
                    "message": line.removeprefix(prefix),
                }
            )
    return sorted(rows, key=lambda row: (str(row["path"]), int(row["line"])))


def report_rows(
    report: ModelValidationReport, root: Path
) -> list[dict[str, str | int]]:
    return normalized_rows("\n".join(f.message for f in report.findings), root)
