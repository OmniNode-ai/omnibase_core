# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared fixture construction and canonical finding normalization."""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_markdown_links_check_compute.runtime_markdown_links_check import (
    build_request,
)

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]
FIXTURES = REPO / "tests/fixtures/validator_parity/markdown_links"


def make_parity_corpus(root: Path, case: str) -> Path:
    corpus = json.loads((FIXTURES / "corpus.json").read_text())[case]
    root.mkdir(parents=True, exist_ok=True)
    for name, source in corpus["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    for name, encoded in corpus.get("binary_sources", {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes.fromhex(encoded))
    config = root / ".markdown-link-check.json"
    config.write_text(json.dumps(corpus["config"]))
    return config


def normalize_parity_report(
    report: ModelValidationReport, root: Path
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        rows.append(
            {
                "path": str(Path(path).relative_to(root)),
                "line": int(line),
                "target": finding.evidence["target"],
                "message": finding.message.replace(str(root), "<ROOT>").replace(
                    str(root.parent), "<ROOT_PARENT>"
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (str(row["path"]), int(str(row["line"])), str(row["target"])),
    )


def parity_request(
    root: Path, config: Path, paths: list[Path] | None = None
) -> ModelMarkdownLinksCheckInput:
    return build_request(root, paths or [], config, None)[0]
