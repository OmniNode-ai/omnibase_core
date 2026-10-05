# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime modes and fail-closed I/O behavior in isolated repositories."""

import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_release_identity_check_compute.runtime_release_identity_check import (
    main,
)
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)

from .conftest import cases, checkout, git

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("filename", "status", "code"),
    [("docs/example.md", "PASS", 0), ("src/example.py", "FAIL", 1)],
)
def test_parity_runtime_filenames(filename, status, code, tmp_path):
    root = checkout(
        tmp_path / "repo", next(case for case in cases() if case["name"] == "equal")
    )
    destination = tmp_path / "report.json"
    assert (
        main(["--root", str(root), filename, "--report-json", str(destination)]) == code
    )
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == status
    )


def test_parity_runtime_zero_files(tmp_path):
    destination = tmp_path / "report.json"
    assert main(["--root", str(tmp_path), "--report-json", str(destination)]) == 1
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == "ERROR"
    )


def test_parity_runtime_unreadable_pyproject(tmp_path, monkeypatch):
    root = checkout(tmp_path / "repo", cases()[0])
    original = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == root / "pyproject.toml":
            raise PermissionError("fixture permission denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    destination = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(destination)]) == 1
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert "permission denied" in report.findings[0].message


def test_parity_runtime_staged_is_not_a_core_flag(tmp_path):
    case = next(case for case in cases() if case["name"] == "equal")
    root = checkout(tmp_path / "repo", case)
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(root), "--staged"])
    assert exc.value.code == 2


def test_parity_runtime_core_no_tags(tmp_path, capsys):
    case = next(case for case in cases() if case["name"] == "no_tags")
    root = checkout(tmp_path / "repo", case)
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.1"\n')
    destination = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(destination)]) == 0
    assert (
        capsys.readouterr().out
        == "OK: no published tag yet — release-identity bump not required.\n"
    )
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == "PASS"
    )


def test_parity_runtime_invalid_toml(tmp_path):
    root = checkout(tmp_path / "repo", cases()[0])
    (root / "pyproject.toml").write_text("[broken\n")
    destination = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(destination)]) == 2
    assert (
        ModelValidationReport.model_validate_json(
            destination.read_text()
        ).overall_status
        == "ERROR"
    )


@pytest.mark.parametrize("project", ['"invalid"', "[]", "0"])
def test_parity_runtime_non_table_project_exit(project, tmp_path):
    root = checkout(tmp_path / "repo", cases()[0])
    (root / "pyproject.toml").write_text(f"project = {project}\n")
    destination = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(destination)]) == 1
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "ERROR"
    assert "has no attribute 'get'" in report.findings[0].message


@pytest.mark.parametrize("marker", ["shallow", "bundle"])
def test_parity_runtime_tagless_provenance(marker, tmp_path):
    case = next(case for case in cases() if case["name"] == "no_tags")
    if marker == "shallow":
        case = {**case, "topology": "shallow"}
    root = checkout(tmp_path / "repo", case)
    if marker == "bundle":
        git(root, "config", "remote.origin.url", "fixture.bundle")
    destination = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(destination)]) == 0
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "PASS"
    assert not report.findings


@pytest.mark.parametrize("operation", ["tags", "diff", "merge_base"])
@pytest.mark.parametrize("case_name", ["ahead", "equal"])
def test_parity_runtime_git_failure_matches_core(
    operation, case_name, tmp_path, monkeypatch
):
    root = checkout(
        tmp_path / "repo", next(case for case in cases() if case["name"] == case_name)
    )
    original = NodeReleaseIdentityGatherEffect._git

    def failed(repo, *args):
        selected = (
            (operation == "tags" and args[0] == "tag")
            or (operation == "diff" and args[0] == "diff")
            or (operation == "merge_base" and args[0] == "merge-base")
        )
        if selected:
            return subprocess.CompletedProcess(
                ["git", *args], 128, "", "fixture Git failure"
            )
        return original(repo, *args)

    monkeypatch.setattr(NodeReleaseIdentityGatherEffect, "_git", staticmethod(failed))
    destination = tmp_path / "report.json"
    expected_code = 1 if case_name == "equal" and operation == "merge_base" else 0
    assert (
        main(["--root", str(root), "--base", "base", "--report-json", str(destination)])
        == expected_code
    )
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == ("FAIL" if expected_code else "PASS")
    assert len(report.findings) == expected_code


def test_parity_runtime_failed_merged_tags_uses_full_list(tmp_path, monkeypatch):
    root = checkout(tmp_path / "repo", cases()[0])
    original = NodeReleaseIdentityGatherEffect._git

    def failed_merged(repo, *args):
        if args[:2] == ("tag", "--merged"):
            return subprocess.CompletedProcess(
                ["git", *args], 128, "", "unresolvable anchor"
            )
        return original(repo, *args)

    monkeypatch.setattr(
        NodeReleaseIdentityGatherEffect, "_git", staticmethod(failed_merged)
    )
    assert main(["--root", str(root)]) == 0


@pytest.mark.parametrize(
    "selector", [["--base", "base"], ["--changed-file", "docs/foo.md"], ["src/foo.py"]]
)
def test_parity_runtime_staged_selector_errors(selector, tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--root", str(tmp_path), "--staged", *selector])
    assert exc.value.code == 2
