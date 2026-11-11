# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23840: the lineage gate resolves a git-derived version at a dev tag.

A package that takes its version from git (hatch-vcs) has no project.version at the
tag commit. Real git proves that the gate then works the version out the way the
build does (next patch, dev distance, commit id), still refuses a lock entry whose
commit, distance or commit id differs, and still refuses a version it cannot derive.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.models.validation.model_dev_tag_lineage_request import (
    ModelDevTagLineageRequest,
)
from omnibase_core.nodes.node_dev_tag_lineage_effect.handler import (
    NodeDevTagLineageEffect,
)
from omnibase_core.validation.checker_dev_tag_lineage import (
    check_dev_tag_lineage,
    load_policy,
    parse_candidates,
    parse_lock,
)
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

DERIVED = (
    '[project]\nname = "package"\ndynamic = ["version"]\n'
    '[tool.hatch.version]\nsource = "vcs"\n'
)


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def commit(repository: Path, name: str, pyproject: str | None = None) -> str:
    if pyproject is not None:
        (repository / "pyproject.toml").write_text(pyproject)
    (repository / name).write_text(name)
    git(repository, "add", "-A")
    git(repository, "commit", "-m", name)
    return git(repository, "rev-parse", "HEAD")


@pytest.fixture
def origin(tmp_path: Path) -> tuple[Path, str, str]:
    """Release tag v2.3.3, two commits after it, the second one tagged as a dev merge."""
    repository = tmp_path / "origin"
    repository.mkdir()
    git(repository, "init", "--initial-branch=dev")
    git(repository, "config", "user.name", "Fixture")
    git(repository, "config", "user.email", "fixture@example.test")
    git(repository, "config", "uploadpack.allowFilter", "true")
    git(repository, "config", "uploadpack.allowAnySHA1InWant", "true")
    commit(repository, "release.txt", DERIVED)
    git(repository, "tag", "-a", "v2.3.3", "-m", "release")
    commit(repository, "first.txt")
    dev = commit(repository, "second.txt")
    tag = f"dev-20261111150000-{dev[:12]}"
    git(repository, "tag", tag)
    commit(repository, "later.txt")
    return repository, dev, tag


def consumer_source(url: str, tag: str, spec: str) -> str:
    return (
        '[project]\nname = "consumer"\nversion = "1.0.0"\n'
        f'dependencies = ["package{spec}"]\n'
        f'[tool.uv.sources]\npackage = {{git = "{url}", tag = "{tag}"}}\n'
    )


def check(
    tmp_path: Path,
    url: str,
    tag: str,
    spec: str = ">=2.3.3,<2.4",
    lock: str | None = None,
) -> list[str | None]:
    consumer = tmp_path / "consumer"
    consumer.mkdir(exist_ok=True)
    (consumer / "pyproject.toml").write_text(consumer_source(url, tag, spec))
    lock_file = consumer / "uv.lock"
    if lock is not None:
        lock_file.write_text(lock)
    elif lock_file.exists():
        lock_file.unlink()
    validator = ValidatorDevTagLineage(
        root=consumer, resolver=NodeDevTagLineageEffect().handle
    )
    return [issue.rule_name for issue in validator.validate(consumer).issues]


def lock_entry(url: str, tag: str, version: str, commit_id: str) -> str:
    return (
        f'[[package]]\nname = "package"\nversion = "{version}"\n'
        f'source = {{git = "{url}?tag={tag}#{commit_id}"}}\n'
    )


def test_derived_version_is_resolved_and_admitted_by_the_range(
    origin, tmp_path: Path
) -> None:
    repository, dev, tag = origin
    policy = load_policy(ValidatorDevTagLineage().contract)
    facts = NodeDevTagLineageEffect().handle(
        ModelDevTagLineageRequest(
            url=repository.as_uri(), tag=tag, branch=policy.branch, policy=policy
        )
    )
    assert facts.commit == dev and facts.on_branch is True
    assert facts.version is not None
    assert facts.version.startswith("2.3.4.dev2+g")
    assert dev.startswith(facts.version.split("+g")[1])
    assert check(tmp_path, repository.as_uri(), tag) == []


@pytest.mark.parametrize("length", [7, 10, 40])
def test_lock_commit_id_length_may_differ_but_not_its_content(
    origin, tmp_path: Path, length: int
) -> None:
    repository, dev, tag = origin
    version = f"2.3.4.dev2+g{dev[:length]}"
    lock = lock_entry(repository.as_uri(), tag, version, dev)
    assert check(tmp_path, repository.as_uri(), tag, lock=lock) == []


@pytest.mark.parametrize(
    "change", ["commit", "distance", "next_patch", "local_part", "no_local_part"]
)
def test_lock_that_does_not_match_the_derived_identity_is_refused(
    origin, tmp_path: Path, change: str
) -> None:
    repository, dev, tag = origin
    version, fragment = f"2.3.4.dev2+g{dev[:9]}", dev
    if change == "commit":
        fragment = "0" * 40
    elif change == "distance":
        version = f"2.3.4.dev3+g{dev[:9]}"
    elif change == "next_patch":
        version = f"2.3.5.dev2+g{dev[:9]}"
    elif change == "local_part":
        version = "2.3.4.dev2+g1234567"
    elif change == "no_local_part":
        version = "2.3.4.dev2"
    lock = lock_entry(repository.as_uri(), tag, version, fragment)
    assert check(tmp_path, repository.as_uri(), tag, lock=lock) == ["lock_mismatch"]


@pytest.mark.parametrize("spec", [">=2.3.5", "<2.3.4", ">=3"])
def test_range_that_does_not_admit_the_derived_version_is_refused(
    origin, tmp_path: Path, spec: str
) -> None:
    repository, _dev, tag = origin
    assert check(tmp_path, repository.as_uri(), tag, spec) == [
        "declared_version_mismatch"
    ]


def test_commit_exactly_at_a_release_tag_derives_the_release_version(
    origin, tmp_path: Path
) -> None:
    repository, _dev, _tag = origin
    release = git(repository, "rev-parse", "v2.3.3^{commit}")
    tag = f"dev-20261111150001-{release[:12]}"
    git(repository, "tag", tag, release)
    lock = lock_entry(repository.as_uri(), tag, "2.3.3", release)
    assert check(tmp_path, repository.as_uri(), tag, lock=lock) == []


def test_dynamic_version_from_another_source_is_unresolved(
    origin, tmp_path: Path
) -> None:
    repository, _dev, _tag = origin
    other = commit(
        repository,
        "other.txt",
        '[project]\nname = "package"\ndynamic = ["version"]\n'
        '[tool.hatch.version]\npath = "version.py"\n',
    )
    tag = f"dev-20261111150002-{other[:12]}"
    git(repository, "tag", tag)
    assert check(tmp_path, repository.as_uri(), tag) == ["lineage_unresolved"]


def test_derived_version_with_no_release_tag_in_history_is_unresolved(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "bare-history"
    repository.mkdir()
    git(repository, "init", "--initial-branch=dev")
    git(repository, "config", "user.name", "Fixture")
    git(repository, "config", "user.email", "fixture@example.test")
    git(repository, "config", "uploadpack.allowFilter", "true")
    git(repository, "config", "uploadpack.allowAnySHA1InWant", "true")
    sha = commit(repository, "only.txt", DERIVED)
    tag = f"dev-20261111150003-{sha[:12]}"
    git(repository, "tag", tag)
    assert check(tmp_path, repository.as_uri(), tag) == ["lineage_unresolved"]


COMMIT = hashlib.sha1(b"derived-version fixture commit").hexdigest()
TAG = f"dev-20261111150000-{COMMIT[:12]}"
URL = "https://example.test/package.git"


def decide(
    version: str, locked: str, derived: bool, fragment: str = COMMIT
) -> list[str | None]:
    """The checker alone, over supplied facts: no git and no network."""
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    candidate = parse_candidates(consumer_source(URL, TAG, ">=2.3.3,<2.4"), policy)[0]
    facts = ModelDevTagLineageFacts(
        tag_exists=True,
        commit=COMMIT,
        version=version,
        version_derived=derived,
        on_branch=True,
        detail="fixture",
    )
    entries = parse_lock(lock_entry(URL, TAG, locked, fragment), policy)
    issues = check_dev_tag_lineage(
        Path("pyproject.toml"), candidate, facts, entries, validator.contract
    )
    return [issue.rule_name for issue in issues]


def test_golden_derived_facts_match_a_lock_with_a_shorter_commit_id() -> None:
    derived = f"2.3.4.dev2+g{COMMIT[:12]}"
    assert decide(derived, f"2.3.4.dev2+g{COMMIT[:7]}", True) == []


@pytest.mark.parametrize(
    ("locked", "fragment"),
    [
        ("2.3.4.dev2+gdeadbee", COMMIT),
        ("2.3.4.dev2+g" + COMMIT[:6], COMMIT),
        ("2.3.4.dev2", COMMIT),
        (f"2.3.4.dev2+g{COMMIT[:7]}", "0" * 40),
    ],
)
def test_error_derived_facts_refuse_every_lock_that_names_another_state(
    locked: str, fragment: str
) -> None:
    derived = f"2.3.4.dev2+g{COMMIT[:12]}"
    assert decide(derived, locked, True, fragment) == ["lock_mismatch"]


def test_a_declared_version_is_still_compared_exactly_with_the_lock() -> None:
    # The commit-id prefix rule belongs to a derived version only.
    assert decide("2.3.4+gabcdef0", "2.3.4+gabcdef0", False) == []
    assert decide("2.3.4+gabcdef0", "2.3.4+gabcdef01", False) == ["lock_mismatch"]
