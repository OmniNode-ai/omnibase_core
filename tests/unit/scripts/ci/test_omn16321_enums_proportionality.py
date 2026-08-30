# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-16321: a provably-additive ``enums/`` diff must not select 44,495 tests.

``enums`` is a ``shared_modules`` entry, so before this change step 3 of
``compute_selection`` escalated on a bare path-prefix match. Measured on
OMN-16998: two appended members plus ten tests -> ``is_full_suite=True``,
``full_suite_reason=shared_module``, 40 shards, ~10h on the contributor's
laptop.

These tests pin BOTH directions. The narrowing case is one test; the rest are
the fail-closed cases, because the only way this change can be wrong is by
narrowing something it should not.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from scripts.ci.detect_test_paths import (
    REPO_ROOT,
    _resolve_enums_diff_additive,
    compute_selection,
    unnarrowable_test_paths,
)
from scripts.ci.test_selection_models import EnumFullSuiteReason

# A real enums module, so the import-graph closure has something to resolve.
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"

ENUMS_FILE = "src/omnibase_core/enums/enum_agent_state.py"
MODELS_FILE = "src/omnibase_core/models/model_node_metadata.py"


def _select(changed: list[str], additive: bool | None):
    return compute_selection(
        changed_files=changed,
        adjacency_path=ADJ,
        ref_name="pr-branch",
        enums_diff_additive=additive,
    )


# --- the narrowing case ----------------------------------------------------


def test_additive_enums_diff_does_not_escalate() -> None:
    """RED before OMN-16321: this returned SHARED_MODULE / 40 shards."""
    selection = _select([ENUMS_FILE], additive=True)
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert selection.split_count < 40


def test_narrowed_selection_still_runs_every_always_run_root() -> None:
    """The narrowing is safe only because nothing leaves the always-run set.

    Exhaustiveness checks that find enum members dynamically (schema sweeps,
    contract validation, registry gates) do not sit on an import edge, so they
    are covered by ``unnarrowable_test_paths`` rather than by the closure.
    """
    selection = _select([ENUMS_FILE], additive=True)
    always_run = unnarrowable_test_paths(REPO_ROOT)
    assert always_run, "fixture drift: the always-run set must not be empty"
    missing = [p for p in always_run if p not in selection.selected_paths]
    assert missing == [], f"narrowed selection dropped always-run roots: {missing}"


# --- fail-closed cases -----------------------------------------------------


@pytest.mark.parametrize(
    "additive",
    [False, None],
    ids=["not-provably-additive", "unclassified"],
)
def test_non_additive_or_unclassified_enums_diff_escalates(
    additive: bool | None,
) -> None:
    """A rename/removal/value-change (False) and an unclassifiable diff (None).

    ``None`` is the shape produced by a missing ``--base-ref`` or an unreadable
    base revision, so this is the guarantee that the pre-OMN-16321 behaviour is
    what ambiguity still gets.
    """
    selection = _select([ENUMS_FILE], additive=additive)
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE
    assert selection.split_count == 40


def test_additive_enums_plus_another_shared_module_still_escalates() -> None:
    """The discharge is scoped to ``enums`` alone — ``models`` escalates on its own."""
    selection = _select([ENUMS_FILE, MODELS_FILE], additive=True)
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


def test_additive_claim_without_an_enums_file_cannot_discharge() -> None:
    """A stale/mis-supplied ``True`` must not discharge some other module's escalation."""
    selection = _select([MODELS_FILE], additive=True)
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


def test_test_infrastructure_still_wins_over_an_additive_enums_diff() -> None:
    """Step 2 runs before step 3 and is untouched by this change."""
    selection = _select([ENUMS_FILE, "tests/conftest.py"], additive=True)
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


# --- the CLI resolver, against a real git repository -----------------------


def _git(repo: Path, *args: str) -> str:
    """Run git against ``repo`` with the ambient git location env SCRUBBED.

    OMN-14891: git exports GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE /
    GIT_COMMON_DIR into every hook environment, and those OVERRIDE both ``-C``
    and ``cwd=``. Without the scrub, this fixture would mutate the REAL
    invoking worktree when the suite runs under a pre-push hook.
    """
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(os.environ),
    ).stdout


@pytest.fixture
def enums_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A git repo with one committed enums module. Returns (root, rel_path, base_sha)."""
    repo = tmp_path / "repo"
    (repo / "src/omnibase_core/enums").mkdir(parents=True)
    rel = "src/omnibase_core/enums/enum_thing.py"
    (repo / rel).write_text(
        "from enum import StrEnum\n\n\nclass EnumThing(StrEnum):\n    A = 'a'\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    return repo, rel, base


def test_resolver_proves_a_real_appended_member(
    enums_repo: tuple[Path, str, str],
) -> None:
    repo, rel, base = enums_repo
    (repo / rel).write_text(
        "from enum import StrEnum\n\n\nclass EnumThing(StrEnum):\n    A = 'a'\n    B = 'b'\n",
        encoding="utf-8",
    )
    assert _resolve_enums_diff_additive(base, repo, [rel]) is True


def test_resolver_refuses_a_real_value_change(
    enums_repo: tuple[Path, str, str],
) -> None:
    repo, rel, base = enums_repo
    (repo / rel).write_text(
        "from enum import StrEnum\n\n\nclass EnumThing(StrEnum):\n    A = 'z'\n",
        encoding="utf-8",
    )
    assert _resolve_enums_diff_additive(base, repo, [rel]) is False


def test_resolver_refuses_a_deleted_enums_file(
    enums_repo: tuple[Path, str, str],
) -> None:
    repo, rel, base = enums_repo
    (repo / rel).unlink()
    assert _resolve_enums_diff_additive(base, repo, [rel]) is False


def test_resolver_refuses_when_one_of_several_files_is_not_additive(
    enums_repo: tuple[Path, str, str],
) -> None:
    """One unprovable file poisons the whole diff — no per-file partial credit."""
    repo, rel, base = enums_repo
    (repo / rel).write_text(
        "from enum import StrEnum\n\n\nclass EnumThing(StrEnum):\n    A = 'a'\n    B = 'b'\n",
        encoding="utf-8",
    )
    other = "src/omnibase_core/enums/enum_new.py"
    (repo / other).write_text("class Broken(:\n", encoding="utf-8")
    assert _resolve_enums_diff_additive(base, repo, [rel, other]) is False


def test_resolver_returns_none_without_a_base_ref(
    enums_repo: tuple[Path, str, str],
) -> None:
    """No base ref -> unclassified -> the caller escalates."""
    repo, rel, _ = enums_repo
    assert _resolve_enums_diff_additive(None, repo, [rel]) is None
    assert _resolve_enums_diff_additive("", repo, [rel]) is None


def test_resolver_returns_none_when_the_diff_has_no_enums_file(
    enums_repo: tuple[Path, str, str],
) -> None:
    repo, _, base = enums_repo
    assert (
        _resolve_enums_diff_additive(base, repo, ["src/omnibase_core/models/m.py"])
        is None
    )


def test_resolver_refuses_an_unreadable_base_revision(
    enums_repo: tuple[Path, str, str],
) -> None:
    """An unfetched/garbage base ref cannot prove anything."""
    repo, rel, _ = enums_repo
    assert _resolve_enums_diff_additive("0" * 40, repo, [rel]) is False


def test_resolver_ignores_an_inherited_git_dir(
    enums_repo: tuple[Path, str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OMN-14891: an inherited ``GIT_DIR`` must not retarget the base-revision read.

    The selector runs FROM the pre-push hook, where git exports ``GIT_DIR`` /
    ``GIT_WORK_TREE`` into the environment, and those override ``git -C``.
    Unscrubbed, this classifier would answer "is this diff additive?" against
    whatever repository the hook happened to be running for — and a wrong answer
    in the narrowing direction silently under-tests. With the scrub, the decoy
    is ignored and the real base still proves the appended member.
    """
    repo, rel, base = enums_repo
    (repo / rel).write_text(
        "from enum import StrEnum\n\n\nclass EnumThing(StrEnum):\n    A = 'a'\n    B = 'b'\n",
        encoding="utf-8",
    )
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    _git(decoy, "init", "-q")
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))

    assert _resolve_enums_diff_additive(base, repo, [rel]) is True
