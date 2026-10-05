# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent characterization from the unmodified core script."""

import io
import json

import pytest

from omnibase_core.models.nodes.release_identity_check.model_release_identity_gather_input import (
    ModelReleaseIdentityGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_release_identity_check_compute.handler import (
    NodeReleaseIdentityCheckCompute,
)
from omnibase_core.nodes.node_release_identity_check_compute.runtime_release_identity_check import (
    main,
)
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)

from .conftest import CORPUS, REPO, argv, cases, checkout, report_rows

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["name"])
def test_parity_golden(case, tmp_path, monkeypatch, capsys):
    root = checkout(tmp_path / "repo", case)
    monkeypatch.setattr("sys.stdin", io.StringIO(str(case.get("stdin", ""))))
    destination = tmp_path / "report.json"
    code = main(["--root", str(root), "--report-json", str(destination), *argv(case)])
    output = capsys.readouterr()
    expected = json.loads((CORPUS / "golden.json").read_text())[case["name"]]
    assert code == expected["exit_code"]
    assert output.out.replace(str(root), "<root>") == expected["stdout"]
    assert output.err.replace(str(root), "<root>") == expected["stderr"]
    assert report_rows(destination.read_text(), root) == expected["findings"]
    args = argv(case)
    explicit = tuple(
        args[index + 1] for index, arg in enumerate(args) if arg == "--changed-file"
    )
    if explicit == ("-",):
        explicit = tuple(
            line.strip()
            for line in str(case.get("stdin", "")).splitlines()
            if line.strip()
        )
    base = args[args.index("--base") + 1] if "--base" in args else None
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(
            repo_root=str(root), base=base, explicit_paths=explicit
        )
    )
    assert len(facts.files) > 0
    report = (
        ModelValidationReport.from_runtime_errors(
            "check-release-identity", facts.runtime_errors
        )
        if facts.runtime_errors
        else NodeReleaseIdentityCheckCompute().handle(facts)
    )
    assert report_rows(report.model_dump_json(), root) == expected["findings"]


@pytest.mark.parametrize("base", [None, "origin/dev"])
def test_parity_repository_full_tree(base, tmp_path, capsys):
    destination = tmp_path / "report.json"
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(repo_root=str(REPO), base=base)
    )
    assert len(facts.files) > 0
    expected = json.loads((CORPUS / "golden.json").read_text())["repository"][
        base or "default"
    ]
    report = NodeReleaseIdentityCheckCompute().handle(facts)
    assert report_rows(report.model_dump_json(), REPO) == expected["findings"]
    assert report.overall_status == expected["status"]
    args = ["--root", str(REPO), "--report-json", str(destination)]
    if base:
        args.extend(["--base", base])
    assert main(args) == expected["exit_code"]
    output = capsys.readouterr()
    assert output.out.replace(str(REPO), "<root>") == expected["stdout"]
    assert output.err.replace(str(REPO), "<root>") == expected["stderr"]
    assert report_rows(destination.read_text(), REPO) == expected["findings"]
