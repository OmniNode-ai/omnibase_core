# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent old-script-generated offline parity goldens."""

import json
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_markdown_links_check_compute.handler import (
    NodeMarkdownLinksCheckCompute,
)
from omnibase_core.nodes.node_markdown_links_check_compute.runtime_markdown_links_check import (
    main,
)

from .parity_support import (
    FIXTURES,
    REPO,
    make_parity_corpus,
    normalize_parity_report,
    parity_request,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("case", ["pass", "fail", "edge", "decoded", "headings"])
def test_parity_markdown_links_golden(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / case
    config = make_parity_corpus(root, case)
    golden = json.loads((FIXTURES / "golden.json").read_text())[case]
    request = parity_request(root, config)
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert normalize_parity_report(report, root) == golden["findings"]
    report_path = tmp_path / "report.json"
    assert (
        main(["--root", str(root), "--report-json", str(report_path)])
        == golden["exit_code"]
    )
    saved = ModelValidationReport.model_validate_json(report_path.read_text())
    assert normalize_parity_report(saved, root) == golden["findings"]
    assert (
        capsys.readouterr()
        .out.replace(str(root), "<ROOT>")
        .replace(str(root.parent), "<ROOT_PARENT>")
        == golden["stdout"]
    )


def test_parity_markdown_links_repository_golden(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = [*REPO.glob("*.md"), *REPO.joinpath("docs").rglob("*.md")]
    request = parity_request(REPO, REPO / ".markdown-link-check.json", paths)
    assert len(request.files) > 0
    golden = json.loads((FIXTURES / "golden.json").read_text())["repository"]
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert normalize_parity_report(report, REPO) == golden["findings"]
    assert (0 if report.overall_status == "PASS" else 1) == golden["exit_code"]
    report_path = tmp_path / "tree-report.json"
    assert (
        main(["--root", str(REPO), "--report-json", str(report_path)])
        == golden["exit_code"]
    )
    saved = ModelValidationReport.model_validate_json(report_path.read_text())
    assert normalize_parity_report(saved, REPO) == golden["findings"]
    assert capsys.readouterr().out == golden["stdout"]
