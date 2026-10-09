# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent characterization from the unmodified core script."""

import io
import json
import tomllib

import pytest
from packaging.version import InvalidVersion, Version

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


@pytest.mark.parametrize("published", ["live", "equal"])
@pytest.mark.parametrize("base", [None, "origin/dev"])
def test_parity_repository_full_tree(base, published, tmp_path, capsys, monkeypatch):
    """Check the live tree without assuming its version is ahead of its tags.

    Fixed repositories above retain exact golden output. This checkout may be
    a release commit or a PR merge onto one, so its expected verdict must account
    for its version, reachable tags and source diff. The equal-tag variant keeps
    that CI regression covered even in a checkout with older or missing tags.
    """
    version = Version(
        tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    )
    if published == "equal":
        original = NodeReleaseIdentityGatherEffect._stdout

        def published_version(self, root, *args):
            if args[0] == "tag":
                return f"v{version}"
            return original(self, root, *args)

        monkeypatch.setattr(
            NodeReleaseIdentityGatherEffect, "_stdout", published_version
        )
    destination = tmp_path / "report.json"
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(repo_root=str(REPO), base=base)
    )
    assert len(facts.files) > 0
    assert not facts.runtime_errors
    assert facts.pyproject_version_raw == str(version)
    versions = []
    for tag in facts.published_tags:
        try:
            versions.append(Version(tag.removeprefix("v")))
        except InvalidVersion:
            continue
    latest = max(versions, default=None)
    source_changed = facts.changed_files is None or any(
        path.startswith("src/") for path in facts.changed_files
    )
    violation = latest is not None and source_changed and version <= latest
    expected_rows = []
    expected_message = ""
    if violation:
        expected_message = (
            "FAIL: packaged source changed but pyproject version "
            f"{version} is NOT ahead of the latest published version "
            f"{latest} (OMN-13411 release-identity gate)."
        )
        expected_rows.append(
            {
                "path": "pyproject.toml",
                "line": 1,
                "message": expected_message,
            }
        )
    report = NodeReleaseIdentityCheckCompute().handle(facts)
    assert report_rows(report.model_dump_json(), REPO) == expected_rows
    assert report.overall_status == ("FAIL" if violation else "PASS")
    args = ["--root", str(REPO), "--report-json", str(destination)]
    if base:
        args.extend(["--base", base])
    assert main(args) == int(violation)
    output = capsys.readouterr()
    if violation:
        assert output.out == ""
        assert output.err.startswith(expected_message + "\n")
        assert report.findings[0].rule_id == "version_not_ahead"
    else:
        assert output.out.startswith("OK: ")
        assert output.err == ""
    assert report_rows(destination.read_text(), REPO) == expected_rows
