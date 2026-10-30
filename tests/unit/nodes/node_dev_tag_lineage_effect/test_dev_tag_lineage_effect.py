# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Real git proves lineage decisions without network or inherited repository state."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_dev_tag_lineage_request import (
    ModelDevTagLineageRequest,
)
from omnibase_core.nodes.node_dev_tag_lineage_effect.handler import (
    NodeDevTagLineageEffect,
)
from omnibase_core.nodes.node_dev_tag_lineage_effect.runtime_dev_tag_lineage import run
from omnibase_core.validation.checker_dev_tag_lineage import load_policy
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def origin(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    repository = tmp_path / "origin"
    repository.mkdir()
    git(repository, "init", "--initial-branch=dev")
    git(repository, "config", "user.name", "Fixture")
    git(repository, "config", "user.email", "fixture@example.test")
    git(repository, "config", "uploadpack.allowFilter", "true")
    git(repository, "config", "uploadpack.allowAnySHA1InWant", "true")
    project = repository / "pyproject.toml"
    project.write_text('[project]\nname = "package"\nversion = "2.3.4"\n')
    git(repository, "add", "pyproject.toml")
    git(repository, "commit", "-m", "dev version")
    dev = git(repository, "rev-parse", "HEAD")
    tag = f"dev-20261029143607-{dev[:12]}"
    git(repository, "tag", tag)
    git(repository, "tag", "-a", f"dev-20261029143608-{dev[:12]}", "-m", "annotated")
    git(repository, "switch", "-c", "side")
    project.write_text('[project]\nname = "package"\nversion = "2.3.5"\n')
    git(repository, "add", "pyproject.toml")
    git(repository, "commit", "-m", "side version")
    side = git(repository, "rev-parse", "HEAD")
    side_tag = f"dev-20261029143609-{side[:12]}"
    git(repository, "tag", side_tag)
    git(repository, "switch", "dev")
    # The valid tag is deliberately behind the tip: ancestry needs history.
    (repository / "later.txt").write_text("later dev commit")
    git(repository, "add", "later.txt")
    git(repository, "commit", "-m", "later dev")
    return repository, dev, tag, side, side_tag


def source(url: str, tag: str, version: str = "2.3.4") -> str:
    return f'[project]\nname = "consumer"\nversion = "1.0.0"\ndependencies = ["package=={version}"]\n[tool.uv.sources]\npackage = {{git = "{url}", tag = "{tag}"}}\n'


def check(
    tmp_path: Path, url: str, tag: str, version: str = "2.3.4", lock: str | None = None
) -> list[str | None]:
    consumer = tmp_path / "consumer"
    consumer.mkdir(exist_ok=True)
    (consumer / "pyproject.toml").write_text(source(url, tag, version))
    if lock is not None:
        (consumer / "uv.lock").write_text(lock)
    validator = ValidatorDevTagLineage(
        root=consumer, resolver=NodeDevTagLineageEffect().handle
    )
    return [issue.rule_name for issue in validator.validate(consumer).issues]


def test_real_dev_merge_tag_and_annotated_tag_pass(origin, tmp_path: Path) -> None:
    repository, dev, tag, _side, _side_tag = origin
    assert check(tmp_path, repository.as_uri(), tag) == []
    assert check(tmp_path, repository.as_uri(), f"dev-20261029143608-{dev[:12]}") == []


def test_made_up_tag_is_absent(origin, tmp_path: Path) -> None:
    repository, *_ = origin
    assert check(tmp_path, repository.as_uri(), "dev-20261029143607-000000000000") == [
        "tag_absent"
    ]


def test_side_branch_tag_fails_ancestry(origin, tmp_path: Path) -> None:
    repository, _dev, _tag, _side, side_tag = origin
    assert check(tmp_path, repository.as_uri(), side_tag, "2.3.5") == ["tag_off_branch"]


def test_wrong_suffix_is_refused(origin, tmp_path: Path) -> None:
    repository, dev, *_ = origin
    tag = "dev-20261029143607-000000000000"
    git(repository, "tag", tag, dev)
    assert check(tmp_path, repository.as_uri(), tag) == ["tag_suffix_mismatch"]


def test_declared_version_is_refused(origin, tmp_path: Path) -> None:
    repository, _dev, tag, *_ = origin
    assert check(tmp_path, repository.as_uri(), tag, "2.3.5") == [
        "declared_version_mismatch"
    ]


@pytest.mark.parametrize(
    "change", ["clean", "version", "tag", "commit", "missing", "duplicate"]
)
def test_real_lock_identity(origin, tmp_path: Path, change: str) -> None:
    repository, dev, tag, *_ = origin
    entry = f'[[package]]\nname = "package"\nversion = "2.3.4"\nsource = {{git = "{repository.as_uri()}?tag={tag}#{dev}"}}\n'
    lock = entry
    if change == "version":
        lock = lock.replace("2.3.4", "2.3.5")
    elif change == "tag":
        lock = lock.replace("tag=dev-", "tag=bad-")
    elif change == "commit":
        lock = lock.replace(f"#{dev}", f"#{'0' * 40}")
    elif change == "missing":
        lock = "version = 1"
    elif change == "duplicate":
        lock += entry
    assert check(tmp_path, repository.as_uri(), tag, lock=lock) == (
        [] if change == "clean" else ["lock_mismatch"]
    )


def test_unreachable_url_is_unresolved(tmp_path: Path) -> None:
    assert check(
        tmp_path, (tmp_path / "missing.git").as_uri(), "dev-20261029143607-000000000000"
    ) == ["lineage_unresolved"]


def test_tag_pointing_to_blob_is_unresolved(origin, tmp_path: Path) -> None:
    repository, *_ = origin
    blob = git(repository, "hash-object", "pyproject.toml")
    tag = f"dev-20261029143607-{blob[:12]}"
    git(repository, "tag", tag, blob)
    assert check(tmp_path, repository.as_uri(), tag) == ["lineage_unresolved"]


def test_missing_branch_and_unreadable_version_are_unresolved(
    origin, tmp_path: Path
) -> None:
    repository, _dev, tag, *_ = origin
    effect = NodeDevTagLineageEffect()
    policy = load_policy(ValidatorDevTagLineage().contract)
    facts = effect.handle(
        ModelDevTagLineageRequest(
            url=repository.as_uri(), tag=tag, branch="missing", policy=policy
        )
    )
    assert facts.tag_exists is True and facts.on_branch is None
    git(repository, "rm", "pyproject.toml")
    git(repository, "commit", "-m", "missing project")
    sha = git(repository, "rev-parse", "HEAD")
    missing_tag = f"dev-20261029143607-{sha[:12]}"
    git(repository, "tag", missing_tag)
    assert check(tmp_path, repository.as_uri(), missing_tag) == ["lineage_unresolved"]


def test_inherited_git_location_and_config_cannot_redirect(
    origin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _dev, tag, *_ = origin
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "bad"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "bad"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "never")
    assert check(tmp_path, repository.as_uri(), tag) == []


def test_cli_uses_contract_outside_checkout_and_reports_errors(
    origin,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, _dev, tag, *_ = origin
    consumer = tmp_path / "external"
    consumer.mkdir()
    project = consumer / "pyproject.toml"
    project.write_text(source(repository.as_uri(), tag))
    monkeypatch.chdir(consumer)
    assert run(["--report-json", str(tmp_path / "pass.json")]) == 0
    project.write_text(source(repository.as_uri(), "dev-20261029143607-000000000000"))
    assert (
        run(["--package", "PACKAGE", "--report-json", str(tmp_path / "fail.json")]) == 1
    )
    assert "tag_absent" in capsys.readouterr().out
    assert run(["--overlay", str(tmp_path / "missing.yaml")]) == 1


def test_request_policy_controls_git_binary_and_completeness_guard(origin) -> None:
    repository, _dev, tag, *_ = origin
    policy = load_policy(ValidatorDevTagLineage().contract)
    effect = NodeDevTagLineageEffect()
    missing = effect.handle(
        ModelDevTagLineageRequest(
            url=repository.as_uri(),
            tag=tag,
            branch=policy.branch,
            policy=policy.model_copy(
                update={"git_binary": str(repository / "missing-git")}
            ),
        )
    )
    assert missing.tag_exists is None and missing.commit is None
    incomplete = effect.handle(
        ModelDevTagLineageRequest(
            url=repository.as_uri(),
            tag=tag,
            branch=policy.branch,
            policy=policy.model_copy(
                update={"shallow_arguments": ("rev-parse", "--is-bare-repository")}
            ),
        )
    )
    assert incomplete.tag_exists is True and incomplete.commit is not None
    assert incomplete.version == "2.3.4" and incomplete.on_branch is None


def test_timeout_is_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    from omnibase_core.nodes.node_dev_tag_lineage_effect import handler

    policy = load_policy(ValidatorDevTagLineage().contract)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=policy.timeout_seconds)

    monkeypatch.setattr(handler.subprocess, "run", timeout)
    facts = NodeDevTagLineageEffect().handle(
        ModelDevTagLineageRequest(
            url="file:///unused",
            tag="dev-20261029143607-000000000000",
            branch=policy.branch,
            policy=policy,
        )
    )
    assert facts.tag_exists is None and facts.on_branch is None
    assert "timed out" in facts.detail


def test_project_name_policy_controls_version_document(origin) -> None:
    repository, _dev, _tag, *_ = origin
    git(repository, "mv", "pyproject.toml", "component.toml")
    git(repository, "commit", "-m", "alternate project filename")
    commit = git(repository, "rev-parse", "HEAD")
    tag = f"dev-20261029143607-{commit[:12]}"
    git(repository, "tag", tag)
    policy = load_policy(ValidatorDevTagLineage().contract).model_copy(
        update={"project_name": "component.toml"}
    )
    facts = NodeDevTagLineageEffect().handle(
        ModelDevTagLineageRequest(
            url=repository.as_uri(), tag=tag, branch=policy.branch, policy=policy
        )
    )
    assert facts.tag_exists is True and facts.on_branch is True
    assert facts.commit == commit and facts.version == "2.3.4"
