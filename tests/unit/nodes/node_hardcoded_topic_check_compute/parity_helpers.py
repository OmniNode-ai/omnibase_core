# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shared corpus materialization and canonical finding normalization."""

from __future__ import annotations

import json
import re
from pathlib import Path

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "tests/fixtures/validator_parity/hardcoded_topic"


def materialize_parity_corpus(root: Path) -> list[ModelSourceFile]:
    files = []
    for case in json.loads((FIXTURES / "corpus.json").read_text()):
        path = root / case["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        source = "onex".join(case["source_parts"])
        data = source.encode("utf-8") + bytes(case.get("trailing_bytes", []))
        path.write_bytes(data)
        files.append(
            ModelSourceFile(
                path=str(path), source=data.decode("utf-8", errors="replace")
            )
        )
    return files


def normalize_parity_stdout(output: str, root: Path) -> list[dict[str, str | int]]:
    rows = []
    for line in output.splitlines():
        match = re.match(r"^(.*):(\d+): (\[.*)$", line)
        if match:
            path = str(Path(match[1]).relative_to(root))
            rows.append(
                {
                    "path": path,
                    "line": int(match[2]),
                    "message": f"{path}:{match[2]}: {match[3]}",
                }
            )
    return rows


def normalize_parity_report(
    report: ModelValidationReport, root: Path
) -> list[dict[str, str | int]]:
    return normalize_parity_stdout("\n".join(f.message for f in report.findings), root)


def read_parity_golden() -> dict[str, object]:
    golden = json.loads((FIXTURES / "golden.json").read_text())
    for row in golden["findings"]:
        row["message"] = "onex".join(row.pop("message_parts"))
    return golden
