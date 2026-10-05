# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent SPDX parity against per-file output captured from the old script."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.spdx_headers_check.model_spdx_headers_check_input import (
    ModelSpdxHeadersCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_spdx_headers_check_compute.handler import (
    NodeSpdxHeadersCheckCompute,
)
from omnibase_core.nodes.node_spdx_headers_check_compute.runtime_spdx_headers_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

from .parity_support import CORPUS, REPO_ROOT, materialize_corpus, report_rows

pytestmark = pytest.mark.unit


def test_spdx_golden_corpus(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    paths = materialize_corpus(tmp_path)
    golden = json.loads((CORPUS / "golden.json").read_text())
    assert {path.name for path in paths} == set(golden)
    for path in paths:
        expected = golden[path.name]
        report = NodeSpdxHeadersCheckCompute().handle(
            ModelSpdxHeadersCheckInput(
                files=[ModelSourceFile(path=str(path), source=path.read_text())]
            )
        )
        assert report_rows(report, tmp_path) == expected["findings"]
        report_path = tmp_path / "report.json"
        assert (
            main([str(path), "--report-json", str(report_path)])
            == expected["exit_code"]
        )
        captured = capsys.readouterr()
        assert captured.out.replace(str(tmp_path) + "/", "") == expected["stdout"]
        assert captured.err.replace(str(tmp_path) + "/", "") == expected["stderr"]
        runtime_report = ModelValidationReport.model_validate_json(
            report_path.read_text()
        )
        assert report_rows(runtime_report, tmp_path) == expected["findings"]


def test_spdx_repo_tree_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The tree the original script passed at the PR base still passes (CI scope)."""
    patterns = [
        f"{root}/**/*{extension}"
        for root in ("src", "tests", "scripts", "examples")
        for extension in (".py", ".sh", ".bash", ".yml", ".yaml", ".toml")
    ]
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", *patterns],
        cwd=REPO_ROOT,
        env=scrub_git_location_env({"PATH": "/usr/bin:/bin:/usr/local/bin"}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    paths = [
        str(REPO_ROOT / path)
        for path in tracked
        if path
        and (REPO_ROOT / path).is_file()
        and not path.startswith(("archived/", "archive/"))
    ]
    assert paths
    assert main([*paths, "--report-json", str(tmp_path / "repo.json")]) == 0
    assert capsys.readouterr().out == ""
