# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""End-to-end proof against committed base manifests and the live checkout."""

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.runtime_required_context_producer_check import (
    main,
)

from .conftest import CONTEXT, MANIFEST, WORKFLOW, commit, git, manifest, row

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("change", "code", "rule"),
    [
        ("clean", 0, None),
        ("delete_workflow", 1, "producer_missing"),
        ("rename_workflow", 1, "producer_missing"),
        ("delete_both", 1, "required_context_dropped"),
        ("advisory", 1, "required_context_dropped"),
        ("rename_job", 1, "producer_missing"),
        ("retire", 0, None),
        ("retire_no_ticket", 1, "required_context_dropped"),
    ],
)
def test_base_protection(repo, tmp_path, capsys, change, code, rule):
    if change in ("delete_workflow", "delete_both", "retire", "retire_no_ticket"):
        (repo / WORKFLOW).unlink()
    if change == "delete_both":
        manifest(repo, [])
    elif change == "advisory":
        manifest(repo, [row(mode="ADVISORY")])
    elif change.startswith("retire"):
        rationale = (
            "Branch protection flipped in OMN-12345" if change == "retire" else "done"
        )
        manifest(repo, [row(mode="RETIRED", rationale=rationale)])
    elif change == "rename_job":
        (repo / WORKFLOW).write_text("jobs:\n  renamed: {}\n")
    elif change == "rename_workflow":
        (repo / WORKFLOW).rename(repo / ".github/workflows/renamed.yml")
    commit(repo)
    output = tmp_path / "report.json"
    assert (
        main(
            ["--root", str(repo), "--base", "origin/main", "--report-json", str(output)]
        )
        == code
    )
    report = ModelValidationReport.model_validate_json(output.read_text())
    assert report.overall_status == ("PASS" if code == 0 else "FAIL")
    captured = capsys.readouterr()
    if rule:
        assert CONTEXT in captured.err
        assert rule in captured.err
        assert rule in {finding.rule_id for finding in report.findings}
        if change in ("delete_workflow", "delete_both", "rename_workflow"):
            assert WORKFLOW in captured.err
        if change == "rename_job":
            assert "job 'produce'" in captured.err
    else:
        assert "OK:" in captured.out
        assert not captured.err


@pytest.mark.parametrize("missing", [False, True])
def test_unresolvable_base_is_an_error_never_a_pass(repo, capsys, missing):
    if missing:
        (repo / WORKFLOW).unlink()
    assert main(["--root", str(repo), "--base", "origin/nope"]) == 2
    err = capsys.readouterr().err
    assert "origin/nope" in err
    assert "does not resolve" in err


@pytest.mark.parametrize(
    "failure",
    [
        "yaml",
        "zero_workflows",
        "missing_manifest",
        "no_gates",
        "manifest_yaml",
        "base_yaml",
    ],
)
def test_errors_fail_closed(repo, tmp_path, capsys, failure):
    if failure == "yaml":
        (repo / WORKFLOW).write_text("jobs: [\n")
    elif failure == "zero_workflows":
        for path in (repo / ".github/workflows").iterdir():
            path.unlink()
    elif failure == "missing_manifest":
        (repo / MANIFEST).unlink()
    elif failure == "no_gates":
        (repo / MANIFEST).write_text("schema: 3\n")
    else:
        (repo / MANIFEST).write_text("gates: [\n")
        if failure == "base_yaml":
            commit(repo)
            git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            manifest(repo, [row()])
    report_path = tmp_path / "error.json"
    assert (
        main(
            [
                "--root",
                str(repo),
                "--base",
                "origin/main",
                "--report-json",
                str(report_path),
            ]
        )
        == 2
    )
    assert (
        ModelValidationReport.model_validate_json(
            report_path.read_text()
        ).overall_status
        == "ERROR"
    )
    assert "ERROR" in capsys.readouterr().err


def test_base_without_manifest_runs_head_check(repo):
    (repo / MANIFEST).unlink()
    commit(repo)
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    manifest(repo, [row()])
    commit(repo)
    assert main(["--root", str(repo), "--base", "origin/main"]) == 0


def test_git_location_environment_is_scrubbed(repo, monkeypatch, capsys):
    (repo / WORKFLOW).unlink()
    manifest(repo, [])
    commit(repo)
    monkeypatch.setenv("GIT_DIR", "/nonexistent-omn19037-git-dir")
    monkeypatch.setenv("GIT_WORK_TREE", "/nonexistent-omn19037-worktree")
    assert main(["--root", str(repo), "--base", "origin/main"]) == 1
    assert "required_context_dropped" in capsys.readouterr().err


def test_caller_coordinates_in_runtime(repo):
    manifest(
        repo,
        [
            row(job_path=["produce", "inner"]),
            row(
                name="cross_repo / inner",
                workflow="external.yml",
                caller_workflow="producer.yml",
                caller_job="produce",
            ),
        ],
    )
    commit(repo)
    assert main(["--root", str(repo), "--base", "origin/main"]) == 0


def test_live_manifest_producers(capsys):
    root = Path(__file__).resolve().parents[4]
    document = yaml.safe_load((root / MANIFEST).read_text())
    required = sum(row["mode"] == "REQUIRED" for row in document["gates"])
    assert required > 0
    assert main(["--root", str(root)]) == 0
    assert f"{required} REQUIRED rows" in capsys.readouterr().out
