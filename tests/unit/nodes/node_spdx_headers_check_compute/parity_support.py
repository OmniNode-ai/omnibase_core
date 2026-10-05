# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Materialize SPDX fixtures and normalize the original script's diagnostics."""

from __future__ import annotations

import re
from pathlib import Path

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
CORPUS = REPO_ROOT / "tests/fixtures/validator_parity/spdx_headers"


def materialize_corpus(root: Path) -> list[Path]:
    """Expand fixture tokens without introducing bypasses in tracked source."""
    paths: list[Path] = []
    for template in sorted(CORPUS.glob("*.in")):
        path = root / template.name.removesuffix(".in")
        path.write_text(
            template.read_text()
            .replace("{copyright}", "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.")
            .replace("{license}", "# SPDX-License-Identifier: MIT")
            .replace("{bypass}", "# spdx-" + "skip:")
            .replace("{bypass_upper}", "# SPDX-" + "SKIP:"),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def normalized_rows(output: str, root: Path) -> list[dict[str, str | int]]:
    """Keep path, rule, line and the exact per-file message after indentation."""
    rows: list[dict[str, str | int]] = []
    prefix = str(root) + "/"
    for line in output.splitlines():
        if not line.startswith("  "):
            continue
        path, message = line[2:].split(": ", 1)
        match = re.match(r"Line (\d+):", message)
        rows.append(
            {
                "path": path.removeprefix(prefix),
                "rule": "spdx-header",
                "line": int(match[1]) if match else 1,
                "message": line[2:].removeprefix(prefix),
            }
        )
    return sorted(rows, key=lambda row: str(row["path"]))


def report_rows(
    report: ModelValidationReport, root: Path
) -> list[dict[str, str | int]]:
    """Normalize actual finding fields, so provenance and location are checked."""
    prefix = str(root) + "/"
    rows: list[dict[str, str | int]] = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        rows.append(
            {
                "path": path.removeprefix(prefix),
                "rule": finding.rule_id or "",
                "line": int(line),
                "message": finding.message.removeprefix(prefix),
            }
        )
    return sorted(rows, key=lambda row: str(row["path"]))
