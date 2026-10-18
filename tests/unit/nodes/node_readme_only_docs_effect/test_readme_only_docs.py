# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Strict documentation gate acceptance corpus for OMN-17427."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.nodes.readme_only_docs.model_readme_only_docs_input import (
    ModelReadmeOnlyDocsInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler_readme_only_docs import (
    HandlerReadmeOnlyDocs,
)
from omnibase_core.nodes.node_git_file_listing_effect.runtime_readme_only_docs import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], env=scrub_git_location_env(), text=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(
        tmp_path,
        "remote",
        "add",
        "origin",
        "https://github.com/OmniNode-ai/example.git",
    )
    put(tmp_path, "README.md")
    return tmp_path


def put(root: Path, name: str, content: str = "sample prose\n") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    git(root, "add", "--", name)


def run(root: Path):
    return HandlerReadmeOnlyDocs().handle(ModelReadmeOnlyDocsInput(root=root))


@pytest.mark.parametrize(
    "name",
    [
        "guide.md",
        "guide.mdx",
        "guide.rst",
        "guide.adoc",
        "guide.txt",
        "nested/README.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "GUIDE.MD",
        ".md",
        "nested/.txt",
        "docs/renamed.rst",
    ],
)
def test_forbidden_document(repo: Path, name: str) -> None:
    put(repo, name)
    report = run(repo)
    assert report.overall_status == "FAIL"
    assert [f.location for f in report.findings] == [name]


def test_only_root_readme_is_implicit(repo: Path) -> None:
    put(repo, "README.md")
    put(repo, "src/code.py", "print('hello')\n")
    assert run(repo).overall_status == "PASS"


@pytest.mark.parametrize(
    "name",
    [
        "requirements.txt",
        "requirements-dev.txt",
        "nested/requirements.lock.txt",
        "nested/Requirements.TXT",
    ],
)
def test_requirements_cannot_be_excepted(repo: Path, name: str) -> None:
    put(repo, name)
    put(
        repo,
        ".readme-only-docs.yaml",
        "exceptions:\n  - path: '*'\n    reason: test fixtures read as data\n",
    )
    assert any(f.location == name for f in run(repo).findings)


@pytest.mark.parametrize(
    "name",
    [
        "LICENSE.txt",
        "CLAUDE.md",
        "AGENTS.md",
        "plugins/demo/skills/demo/SKILL.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "tests/fixtures/doc.rst",
    ],
)
def test_reasoned_machine_exception(repo: Path, name: str) -> None:
    put(repo, name)
    assert run(repo).overall_status == "FAIL"
    put(
        repo,
        ".readme-only-docs.yaml",
        f"exceptions:\n  - path: '{name}'\n    reason: machine consumer loads this fixture or definition\n",
    )
    assert run(repo).overall_status == "PASS"


@pytest.mark.parametrize(
    "policy",
    [
        "exceptions: ['docs/**']",
        "exceptions:\n  - path: 'docs/**'",
        "exceptions:\n  - path: '**'\n    reason: ' '",
        "exceptions: []\nmode: advisory",
        "[broken",
        "exceptions: []\nexceptions: []",
    ],
)
def test_invalid_policy_fails_closed(repo: Path, policy: str) -> None:
    put(repo, ".readme-only-docs.yaml", policy)
    assert run(repo).overall_status == "ERROR"


def test_unstaged_allowlist_cannot_grant_exception(repo: Path) -> None:
    put(repo, "guide.md")
    (repo / ".readme-only-docs.yaml").write_text(
        "exceptions:\n  - path: guide.md\n    reason: unstaged policy\n"
    )
    assert run(repo).overall_status == "FAIL"


@pytest.mark.parametrize(
    "repository",
    [
        "knowledge_base",
        "knowledge_base_internal",
        "knowledge-base",
        "knowledge-base-internal",
    ],
)
def test_knowledge_base_is_exempt(repo: Path, repository: str) -> None:
    git(
        repo,
        "remote",
        "set-url",
        "origin",
        f"git@github.com:OmniNode-ai/{repository}.git",
    )
    put(repo, "guide.md")
    assert run(repo).overall_status == "PASS"


def test_directory_name_does_not_exempt(repo: Path) -> None:
    renamed = repo.with_name("knowledge_base")
    repo.rename(renamed)
    put(renamed, "guide.md")
    assert run(renamed).overall_status == "FAIL"


def test_rename_to_another_extension_is_refused(repo: Path) -> None:
    put(repo, "guide.md")
    git(repo, "mv", "guide.md", "guide.txt")
    assert [f.location for f in run(repo).findings] == ["guide.txt"]


def test_staged_deletion_and_untracked_docs_are_absent(repo: Path) -> None:
    put(repo, "guide.md")
    git(repo, "rm", "-f", "guide.md")
    (repo / "untracked.md").write_text("prose")
    assert run(repo).overall_status == "PASS"


def test_report_emits_run_and_fire_even_on_error(repo: Path, tmp_path: Path) -> None:
    put(repo, "guide.md")
    target = tmp_path / "report.json"
    assert main(["--root", str(repo), "--report-json", str(target)]) == 1
    events = [
        json.loads(line)
        for line in target.with_name("report.json.events.jsonl")
        .read_text()
        .splitlines()
    ]
    assert [event["kind"] for event in events] == ["run", "fire"]
    assert events[1]["location"] == "guide.md"
    git(repo, "rm", "-f", "guide.md")
    assert main(["--root", str(repo), "--report-json", str(target)]) == 0
    events = [
        json.loads(line)
        for line in target.with_name("report.json.events.jsonl")
        .read_text()
        .splitlines()
    ]
    assert events[-1]["kind"] == "run"
    assert events[-1]["fired_count"] == 0


def test_non_repository_is_error(tmp_path: Path) -> None:
    assert run(tmp_path).overall_status == "ERROR"


def test_readme_deletion_is_refused(repo: Path) -> None:
    git(repo, "rm", "-f", "README.md")
    assert any(f.rule_id == "root-readme-required" for f in run(repo).findings)


def test_invocation_from_subdirectory_still_checks_whole_tree(repo: Path) -> None:
    put(repo, "guide.md")
    nested = repo / "nested"
    nested.mkdir()
    report = run(nested)
    assert [f.location for f in report.findings] == ["guide.md"]


def test_staged_policy_wins_over_unstaged_edit(repo: Path) -> None:
    put(repo, "guide.md")
    put(repo, ".readme-only-docs.yaml", "exceptions: []")
    (repo / ".readme-only-docs.yaml").write_text(
        "exceptions:\n  - path: guide.md\n    reason: unstaged edit\n"
    )
    assert run(repo).overall_status == "FAIL"


def test_cli_configuration_error_emits_events(repo: Path, tmp_path: Path) -> None:
    put(repo, ".readme-only-docs.yaml", "exceptions: ['bad schema']")
    target = tmp_path / "error.json"
    assert main(["--root", str(repo), "--report-json", str(target)]) == 2
    events = [
        json.loads(line)
        for line in target.with_name("error.json.events.jsonl").read_text().splitlines()
    ]
    assert [event["kind"] for event in events] == ["run", "fire"]
    assert events[0]["verdict"] == "ERROR"


def test_core_ci_and_exported_hook_share_the_node() -> None:
    import yaml

    root = Path(__file__).resolve().parents[4]
    hooks = yaml.safe_load((root / ".pre-commit-hooks.yaml").read_text())
    hook = next(item for item in hooks if item["id"] == "readme-only-docs")
    assert (
        hook["entry"]
        == "python -m omnibase_core.nodes.node_git_file_listing_effect.runtime_readme_only_docs"
    )
    assert hook["always_run"] is True and hook["pass_filenames"] is False
    ci = yaml.safe_load((root / ".github/workflows/ci.yml").read_text())
    caller = ci["jobs"]["kb-doc-gate"]
    assert caller["uses"] == "./.github/workflows/kb-doc-gate-reusable.yml"
    assert "if" not in caller and "needs" not in caller
    workflow = yaml.safe_load(
        (root / ".github/workflows/kb-doc-gate-reusable.yml").read_text()
    )
    job = workflow["jobs"]["kb-doc-gate"]
    assert job["name"] == "kb-doc-gate"
    assert workflow.get("on", workflow.get(True)) == {"workflow_call": {}}
    command = next(
        step
        for step in job["steps"]
        if step["name"] == "Refuse tracked documentation and requirements txt"
    )
    assert "if" not in command and "continue-on-error" not in command
    assert (
        "python -m omnibase_core.nodes.node_git_file_listing_effect.runtime_readme_only_docs"
        in command["run"]
    )
    pin = next(step for step in job["steps"] if step.get("id") == "pin")
    assert pin["env"]["WORKFLOW_SHA"] == "${{ job.workflow_sha }}"
    checkout = next(
        step
        for step in job["steps"]
        if step["name"].startswith("Checkout shared validator")
    )
    assert checkout["with"]["ref"] == "${{ steps.pin.outputs.sha }}"
    collect = job["steps"][-1]
    assert collect["if"] == "always()"
    assert collect["with"]["if-no-files-found"] == "error"


def test_merge_group_has_only_the_real_documentation_producer() -> None:
    import yaml

    root = Path(__file__).resolve().parents[4]
    queued = yaml.safe_load(
        (root / ".github/workflows/merge-group-pr-scoped-contexts.yml").read_text()
    )
    assert all(
        job.get("name") != "kb-doc-gate / kb-doc-gate"
        for job in queued["jobs"].values()
    )
