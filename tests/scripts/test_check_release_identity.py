# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the release-identity gate (OMN-13411).

The gate forbids merging a packaged-source change onto an already-published
version string. It is the omnibase_core port of the omnibase_infra release
identity gate (OMN-13412) and the recurrence guard for the OMN-13402/OMN-13405
"unreleased code on a published version" crash.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_release_identity.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_release_identity", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mod():
    return _load_module()


@pytest.mark.unit
def test_passes_when_version_ahead_of_published(mod, monkeypatch):
    """src/** changed, but the version is strictly ahead — gate passes."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.46.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_fails_when_src_changed_and_version_equals_published(mod, monkeypatch):
    """src/** changed and the version equals the published wheel — gate FAILS.

    This is the literal OMN-13405 footgun: core dev HEAD carried unreleased
    modules while still labelled 0.45.0 (== the published wheel).
    """
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 1


@pytest.mark.unit
def test_fails_when_src_changed_and_version_behind_published(mod, monkeypatch):
    """A version BEHIND the latest published tag is also a fail."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.44.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 1


@pytest.mark.unit
def test_exempt_when_no_packaged_source_changed(mod, monkeypatch):
    """A docs/tests/CI-only diff is exempt — the published wheel is unaffected."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: False)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_passes_when_no_published_tag_yet(mod, monkeypatch):
    """A repo with no published tags cannot alias a published version."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.1.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: None)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_config_error_on_missing_version(mod, monkeypatch):
    """A missing project.version is a config error (exit 2), not a pass."""

    def _raise():
        raise ValueError("no project.version")

    monkeypatch.setattr(mod, "_read_pyproject_version", _raise)
    assert mod.main(["--base", "origin/dev"]) == 2


@pytest.mark.unit
def test_packaged_source_changed_detects_src_prefix(mod):
    """The src/ prefix triggers the bump requirement; non-src does not."""
    assert mod._packaged_source_changed(None, ["src/omnibase_core/enums/enum_x.py"])
    assert not mod._packaged_source_changed(
        None, ["docs/foo.md", "tests/test_x.py", ".github/workflows/ci.yml"]
    )


@pytest.mark.unit
def test_explicit_changed_file_overrides_base(mod, monkeypatch):
    """An explicit --changed-file list bypasses git diffing entirely."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    # Explicit src file => changed => must be ahead => fails at 0.45.0.
    assert mod.main(["--changed-file", "src/omnibase_core/foo.py"]) == 1
    # Explicit docs file => not changed => exempt => passes.
    assert mod.main(["--changed-file", "docs/foo.md"]) == 0


def _isolated_checkout(tmp_path: Path, *, published_tag: str) -> Path:
    """Stand the REAL script up in a throwaway repo whose tag set we own.

    ``check_release_identity`` derives its repo root from its own file location
    (``Path(__file__).resolve().parents[1]``) and shells out to ``git`` there,
    so copying the real script + the real ``pyproject.toml`` into
    ``<tmp>/scripts/`` + ``<tmp>/`` makes ``<tmp>`` the root it inspects. Every
    input the gate reads is then under the test's control -- no tags are
    written into, or deleted from, the developer's actual checkout.
    """
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(_SCRIPT, root / "scripts" / _SCRIPT.name)
    shutil.copy2(
        _SCRIPT.resolve().parents[1] / "pyproject.toml", root / "pyproject.toml"
    )

    # Must stay named `scrubbed_git_env`: no_unguarded_git_subprocess keys on a
    # canonical scrub name appearing in the `env=` expression itself, so a
    # differently-named local reads as an unscrubbed ambient env and fails
    # closed -- which is exactly what it did to the first cut of this helper.
    #
    # Called with NO argument on purpose (OMN-18443). Passing ``os.environ``
    # explicitly is a raw process-environment read, which this repo's OMN-17744
    # typed-bootstrap boundary refuses outside the bootstrap capture -- so the
    # two guards pull against each other at this exact line. The scrubber's own
    # default already reads the process environment inside the core library,
    # which satisfies both: the location scrub still happens, and no raw
    # ``os.environ`` token appears here.
    scrubbed_git_env = scrub_git_location_env()
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "smoke"],
        ["tag", published_tag],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, env=scrubbed_git_env)
    return root


def _run_gate(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the gate against ``root`` only.

    The scrub is load-bearing, not ceremony: GIT_DIR / GIT_WORK_TREE override
    ``cwd``, so an ambient one (a git hook exports exactly these -- the
    OMN-14891 case) would make the gate's internal ``git tag --list`` read the
    developer's real checkout instead of the isolated repo, and the isolation
    this whole helper exists to provide would silently evaporate.
    """
    scrubbed_git_env = scrub_git_location_env()
    return subprocess.run(
        [sys.executable, str(root / "scripts" / _SCRIPT.name)],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
        env=scrubbed_git_env,
    )


@pytest.mark.unit
def test_live_invocation_smoke(tmp_path):
    """Real subprocess run of the real script, end to end: version ahead => 0.

    OMN-15603: this smoke used to force a ``v0.45.999999`` tag into the ACTUAL
    repo and assert strict mode exited 0. That fixture was version-fragile by
    construction -- ``_latest_published_version`` takes the MAX over all tags,
    so the synthetic tag only decides the comparison while it outranks every
    real tag. Once ``v0.46.x`` was cut the synthetic tag went inert, the real
    tag became the maximum, and the assertion inverted: with dev's
    ``project.version`` equal to the newest tag (the normal state of the tree
    in the whole window between a release and the next bump) strict mode
    correctly exits 1 and this test failed on every open PR. The gate was
    right; the fixture was wrong. Owning the tag set outright fixes it for
    good, and drops the mutate-then-restore dance on the real checkout that
    OMN-14891 had to harden.
    """
    root = _isolated_checkout(tmp_path, published_tag="v0.0.1")

    result = _run_gate(root)

    assert result.returncode == 0, result.stderr
    assert "ahead of latest published" in result.stdout


@pytest.mark.unit
def test_live_invocation_fails_when_version_is_not_ahead(tmp_path):
    """Live negative: the gate must FAIL, not merely be absent, when behind.

    Exists-but-wrong, end to end through the real subprocess -- a script that
    silently exited 0 on an un-bumped version would pass the positive smoke
    above and still let the OMN-13405 footgun through.
    """
    root = _isolated_checkout(tmp_path, published_tag="v99.0.0")

    result = _run_gate(root)

    assert result.returncode == 1, result.stdout
    assert "is NOT ahead of the latest published version" in result.stderr


# ---------------------------------------------------------------------------
# OMN-18058: the empty-three-dot fallback stays MERGE-BASE anchored.
# ---------------------------------------------------------------------------


def _omn18058_git(repo: Path, *args: str) -> str:
    # OMN-14891: git exports GIT_DIR/GIT_WORK_TREE into every hook environment and
    # those OVERRIDE `-C`, so an unscrubbed fixture would mutate the real worktree.
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    ).stdout


def _omn18058_stale_base_repo(tmp_path: Path) -> Path:
    """A branch with NO commits of its own, after which a peer advanced ``dev``.

    The peer's commit touches packaged source (``src/``), so the two-dot form
    attributes a packaged-source change to a branch that changed nothing.
    """
    origin = tmp_path / "omn18058-origin.git"
    work = tmp_path / "omn18058-work"
    subprocess.run(
        ["git", "init", "-q", "--bare", str(origin)],
        check=True,
        env=scrub_git_location_env(),
    )
    subprocess.run(
        ["git", "init", "-q", str(work)],
        check=True,
        env=scrub_git_location_env(),
    )
    _omn18058_git(work, "config", "user.email", "omn18058@example.invalid")
    _omn18058_git(work, "config", "user.name", "omn18058 fixture")
    _omn18058_git(work, "config", "commit.gpgsign", "false")
    _omn18058_git(work, "checkout", "-q", "-b", "dev")
    (work / "docs").mkdir(parents=True, exist_ok=True)
    (work / "docs" / "base.md").write_text("base\n", encoding="utf-8")
    _omn18058_git(work, "add", "-A")
    _omn18058_git(work, "commit", "-q", "-m", "base")
    _omn18058_git(work, "remote", "add", "origin", str(origin))
    _omn18058_git(work, "push", "-q", "origin", "dev")

    _omn18058_git(work, "checkout", "-q", "-b", "feature")
    _omn18058_git(work, "checkout", "-q", "dev")
    peer = work / "src" / "peer_pkg" / "landed_by_someone_else.py"
    peer.parent.mkdir(parents=True, exist_ok=True)
    peer.write_text("# a peer's packaged-source landing\n", encoding="utf-8")
    _omn18058_git(work, "add", "-A")
    _omn18058_git(work, "commit", "-q", "-m", "a peer's packaged-source landing")
    _omn18058_git(work, "push", "-q", "origin", "dev")

    _omn18058_git(work, "checkout", "-q", "feature")
    _omn18058_git(work, "fetch", "-q", "origin", "dev")
    return work


@pytest.mark.unit
def test_omn18058_empty_branch_diff_never_attributes_a_peers_packaged_source(
    mod, monkeypatch, tmp_path
):
    """OMN-18058: a branch with no commits of its own is exempt, not armed.

    The old fallback used the two-dot ``git diff origin/dev``, which describes
    the difference between two TREES -- so every ``src/`` file a peer landed on
    ``dev`` since the branch point was reported as this branch's change and the
    version gate fired on work the branch never did.
    """
    repo = _omn18058_stale_base_repo(tmp_path)

    # Positive controls, on this same fixture: the three-dot set really is empty
    # (so the fallback under test is the branch that executes), and the two-dot
    # form really does surface the peer's packaged-source file.
    assert _omn18058_git(repo, "diff", "--name-only", "origin/dev...HEAD").strip() == ""
    assert "src/peer_pkg/landed_by_someone_else.py" in _omn18058_git(
        repo, "diff", "--name-only", "origin/dev", "HEAD"
    )

    monkeypatch.setattr(mod, "_REPO_ROOT", repo)
    assert mod._packaged_source_changed("origin/dev", []) is False

    # ...and the fallback still sees this branch's own UNCOMMITTED packaged edit.
    own = repo / "src" / "own_pkg" / "mine.py"
    own.parent.mkdir(parents=True, exist_ok=True)
    own.write_text("# uncommitted, mine\n", encoding="utf-8")
    _omn18058_git(repo, "add", "-A")
    assert mod._packaged_source_changed("origin/dev", []) is True


# ---------------------------------------------------------------------------
# OMN-18443 — the collector must read ONE clock.
#
# The gate reads a VERSION FROM A TREE and a SET OF PUBLISHED RELEASES. On a
# pull_request event GitHub hands the runner refs/pull/N/merge, the merge commit
# it computed at TRIGGER time, while actions/checkout fetches every tag ref at
# RUN time. Collecting the published set with `git tag --list` compared those
# two clocks and refused trees that were correctly versioned when computed.
#
# omnibase_core releases on a tag push rather than on every merge, so its window
# is narrower than the sibling repo's. Narrower is not absent, and it is the
# same collector — fixing it per-repo would be the one-off configuration the
# standing rule forbids.
# ---------------------------------------------------------------------------


def _set_project_version(root: Path, version: str) -> None:
    """Rewrite ``[project].version`` in the throwaway repo's pyproject.toml."""
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    with path.open("rb") as fh:
        current = tomllib.load(fh)["project"]["version"]
    needle = f'version = "{current}"'
    assert needle in text, f"pyproject version line {needle!r} not found verbatim"
    path.write_text(text.replace(needle, f'version = "{version}"', 1), encoding="utf-8")


def _tag_peer_release_off_this_lineage(root: Path, tag: str) -> None:
    """Cut ``tag`` on a lineage HEAD cannot reach — a peer PR's release.

    This is the live topology, not an analogy: the peer's squash merge landed on
    the base branch and the release tagged that merge sha, so the tag's commit
    is not an ancestor of the commit this branch's tree was computed from.
    """
    scrubbed_git_env = scrub_git_location_env()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=scrubbed_git_env,
        ).stdout.strip()

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    git("checkout", "-q", "-b", "omn18443-peer")
    (root / "peer.txt").write_text("peer release\n", encoding="utf-8")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "peer release")
    git("tag", tag)
    git("checkout", "-q", branch)

    # Positive controls on the FIXTURE itself, so no assertion below can pass
    # because the topology silently failed to build.
    all_tags = git("tag", "--list").split()
    merged = git("tag", "--merged", "HEAD").split()
    assert tag in all_tags, f"peer tag never created: {all_tags}"
    assert tag not in merged, f"peer tag IS reachable — not the race: {merged}"


def _isolated_race_checkout(
    tmp_path: Path, *, reachable_tag: str, unreachable_tag: str, version: str
) -> Path:
    """Throwaway repo in the state the sibling repo's PRs were refused in."""
    root = _isolated_checkout(tmp_path, published_tag=reachable_tag)
    _tag_peer_release_off_this_lineage(root, unreachable_tag)
    _set_project_version(root, version)
    return root


@pytest.mark.unit
def test_release_cut_off_this_lineage_does_not_arm_the_gate(tmp_path):
    """AC1 falsifier: a release published after this tree must not refuse it."""
    root = _isolated_race_checkout(
        tmp_path, reachable_tag="v1.0.0", unreachable_tag="v2.0.0", version="2.0.0"
    )

    result = _run_gate(root)

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "ahead of latest published" in result.stdout


@pytest.mark.unit
def test_version_equal_to_a_reachable_release_still_fails(tmp_path):
    """AC2 positive control: the real aliasing invariant must not regress."""
    root = _isolated_race_checkout(
        tmp_path, reachable_tag="v1.0.0", unreachable_tag="v2.0.0", version="1.0.0"
    )

    result = _run_gate(root)

    assert result.returncode == 1, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "is NOT ahead of the latest published version" in result.stderr


@pytest.mark.unit
def test_version_behind_a_reachable_release_still_fails(tmp_path):
    """AC2 positive control, strictly-behind arm: unreachable tags never rescue."""
    root = _isolated_race_checkout(
        tmp_path, reachable_tag="v1.0.0", unreachable_tag="v2.0.0", version="0.9.0"
    )

    result = _run_gate(root)

    assert result.returncode == 1, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "is NOT ahead of the latest published version" in result.stderr


@pytest.mark.unit
def test_published_tags_are_anchored_to_the_evaluated_tree(mod, monkeypatch):
    """The collector asks for tags REACHABLE FROM HEAD, not every tag that exists."""
    seen: list[list[str]] = []

    def fake_git(args: list[str]) -> str:
        seen.append(list(args))
        if args[:2] == ["rev-parse", "--is-shallow-repository"]:
            return "false"
        if args[:2] == ["tag", "--merged"]:
            return "v1.0.0\nv1.0.1"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(mod, "_git", fake_git)

    assert mod._published_tags() == ["v1.0.0", "v1.0.1"]
    assert ["tag", "--merged", "HEAD"] in seen
    assert ["tag", "--list"] not in seen


@pytest.mark.unit
def test_shallow_clone_falls_back_to_the_full_tag_list(mod, monkeypatch):
    """Fail-CLOSED: ancestry is unknowable on a shallow clone.

    ``git tag --merged`` needs the tagged commits' ancestry present; a shallow
    clone can omit it and return FEWER tags, the permissive direction. The
    stricter full list is used instead.
    """
    seen: list[list[str]] = []

    def fake_git(args: list[str]) -> str:
        seen.append(list(args))
        if args[:2] == ["rev-parse", "--is-shallow-repository"]:
            return "true"
        if args[:2] == ["tag", "--merged"]:
            raise AssertionError("must not ancestry-anchor on a shallow clone")
        return "v1.0.0\nv9.9.9"

    monkeypatch.setattr(mod, "_git", fake_git)

    assert mod._published_tags() == ["v1.0.0", "v9.9.9"]
    assert ["tag", "--list"] in seen


@pytest.mark.unit
def test_empty_merged_result_falls_back_to_the_full_tag_list(mod, monkeypatch):
    """Fail-CLOSED: an anchor that resolves no tags is not a pass.

    ``_git`` in this gate swallows a non-zero exit and returns an empty string,
    so a failed ``--merged`` is indistinguishable from a genuinely tag-less
    ancestry. Both take the stricter branch rather than reporting that nothing
    has ever been published.
    """

    def fake_git(args: list[str]) -> str:
        if args[:2] == ["rev-parse", "--is-shallow-repository"]:
            return "false"
        if args[:2] == ["tag", "--merged"]:
            return ""
        return "v1.0.0\nv7.7.7"

    monkeypatch.setattr(mod, "_git", fake_git)

    assert mod._published_tags() == ["v1.0.0", "v7.7.7"]
