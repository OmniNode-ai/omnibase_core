# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Execute the inline writer-app release-cut verdict against real git objects."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
    _step,
)

pytestmark = pytest.mark.unit

PROJECT = '[project]\nname = "x"\nversion = "0.38.69"\n'
BASE_CHANGELOG = "## v0.38.68 (2026-10-07)\n\n### Release\n- previous\n"
SECTION = "## v0.38.69 (2026-10-08)\n\n### Release\n- item\n\n"
CHANGELOG = SECTION + BASE_CHANGELOG

# Mirror the pinned verifier's pure classifiers, including its basename-based
# release allowlist. The workflow must impose the stricter root-path allowlist.
PROBE = dedent("""\
    from pathlib import Path
    import tomllib

    def is_release_artifact_only_diff(paths):
        if not paths:
            return False
        carries_claim = False
        for path in paths:
            name = Path(path).name
            if name == "CHANGELOG.md" or name.startswith("Dockerfile"):
                carries_claim = True
            elif name not in ("pyproject.toml", "uv.lock"):
                return False
        return carries_claim

    def flatten(table, prefix=""):
        result = {}
        for key, value in table.items():
            dotted = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(flatten(value, dotted))
            else:
                result[dotted] = value
        return result

    def classify_dependency_pin_only(paths, *, pyproject_head, pyproject_base):
        if not paths:
            return False, "empty diff"
        if any(Path(path).name not in ("pyproject.toml", "uv.lock") for path in paths):
            return False, "non-manifest path"
        if not any(Path(path).name == "pyproject.toml" for path in paths):
            return True, "lockfile-only diff"
        if pyproject_head is None or pyproject_base is None:
            return False, "manifest content is missing"
        head = flatten(tomllib.loads(pyproject_head))
        base = flatten(tomllib.loads(pyproject_base))
        allowed = ("project.version", "project.dependencies",
                   "project.optional-dependencies", "dependency-groups", "tool.uv.sources")
        changed = [key for key in head.keys() | base.keys() if head.get(key) != base.get(key)]
        if any(not key.startswith(allowed) for key in changed):
            return False, "manifest changes outside dependency-pin keys"
        return True, "version/dependency-pin keys only"
    """)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    return result.stdout.strip()


def _write_files(repo: Path, files: dict[str, str | None]) -> None:
    for name, content in files.items():
        file = repo / name
        if content is None:
            file.unlink(missing_ok=True)
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)


def _prepare(
    tmp_path: Path,
    base_changes: dict[str, str | None],
    head_changes: dict[str, str | None],
    *,
    allow_empty: bool = False,
) -> dict[str, str]:
    workspace = tmp_path / "ws"
    repo = workspace / ".dod-verify/head_home/x"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _write_files(
        repo,
        {
            "pyproject.toml": PROJECT,
            "uv.lock": 'version = "0.38.69"\n',
            "CHANGELOG.md": BASE_CHANGELOG,
            **base_changes,
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _write_files(repo, {"CHANGELOG.md": CHANGELOG, **head_changes})
    _git(repo, "add", ".")
    # Only a fixture that means to be an empty release may commit no change.
    _git(repo, "commit", *(["--allow-empty"] if allow_empty else []), "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    # Neither the version nor the changelog may come from the working tree.
    _write_files(repo, {"pyproject.toml": "not TOML", "CHANGELOG.md": "not a release"})
    runner = tmp_path / "runner"
    runner.mkdir()
    stub = tmp_path / "stub"
    package = stub / "omnimarket"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "occ_content_probe.py").write_text(PROBE)
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "sys.argv = ['-', *sys.argv[2:]]; "
        "exec(compile(sys.stdin.read(), '<stdin>', 'exec'))"
    )
    launcher = tmp_path / "verifier"
    launcher.write_text(
        "#!/bin/bash\n"
        '[ "$1" = -I ] && [ "$2" = - ] || exit 1\n'
        "shift 2\n"
        f"exec {shlex.quote(sys.executable)} -I -c {shlex.quote(code)} "
        f'{shlex.quote(str(stub))} "$@"\n'
    )
    launcher.chmod(0o755)
    return {
        "PATH": "/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
        "RUNNER_TEMP": str(runner),
        "REPO_SHORT": "x",
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "DOD_VERIFY_PY": str(launcher),
    }


@pytest.mark.parametrize(
    ("base_changes", "head_changes", "version"),
    [
        pytest.param({}, {}, "0.38.69", id="infra-changelog-only"),
        pytest.param(
            {
                "CHANGELOG.md": None,
                "pyproject.toml": PROJECT.replace("0.38.69", "0.4.304"),
                "uv.lock": 'version = "0.4.304"\n',
            },
            {
                "CHANGELOG.md": "## v0.4.305 (2026-10-08)\n\n### Release\n- item\n",
                "pyproject.toml": PROJECT.replace("0.38.69", "0.4.305"),
                "uv.lock": 'version = "0.4.305"\n',
            },
            "0.4.305",
            id="omnimarket-new-changelog-and-pins",
        ),
        pytest.param(
            {},
            {"uv.lock": 'version = "0.38.69"\nrevision = 2\n'},
            "0.38.69",
            id="changelog-and-lockfile",
        ),
    ],
)
def test_writer_release_cut_exempts_measured_shapes(
    tmp_path: Path,
    base_changes: dict[str, str | None],
    head_changes: dict[str, str | None],
    version: str,
) -> None:
    env = _prepare(tmp_path, base_changes, head_changes)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "OCC writer app authored a release cut" in result.stdout
    assert f"at {env['HEAD_SHA']}" in result.stdout
    assert f"merge base {env['BASE_SHA']}" in result.stdout
    assert f"release cut adds changelog version {version}" in result.stdout
    assert "OMN-20074" in result.stdout


@pytest.mark.parametrize(
    ("base_changes", "head_changes", "reason"),
    [
        pytest.param(
            {}, {"src/x.py": "x = 1\n"}, "not a release-artifact-only diff", id="source"
        ),
        pytest.param(
            {},
            {".github/workflows/x.yml": "name: x\n"},
            "not a release-artifact-only diff",
            id="workflow",
        ),
        pytest.param(
            {},
            {"Dockerfile": "FROM scratch\n"},
            "outside the root release allowlist",
            id="dockerfile",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": BASE_CHANGELOG, "docs/CHANGELOG.md": SECTION},
            "requires root CHANGELOG.md",
            id="nested-changelog",
        ),
        pytest.param(
            {},
            {"pkg/pyproject.toml": PROJECT},
            "outside the root release allowlist",
            id="nested-project",
        ),
        pytest.param(
            {},
            {"pkg/uv.lock": "version = 1\n"},
            "outside the root release allowlist",
            id="nested-lockfile",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": CHANGELOG.replace("previous", "rewritten")},
            "rewrites or deletes",
            id="rewritten-line",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": CHANGELOG.replace("- previous\n", "")},
            "rewrites or deletes",
            id="deleted-line",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": CHANGELOG.replace("v0.38.69", "v0.38.70")},
            "does not match head project.version",
            id="version-mismatch",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": SECTION + "## v0.38.70 (2026-10-08)\n" + BASE_CHANGELOG},
            "exactly one inserted ## heading",
            id="two-headings",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": "new text\n" + BASE_CHANGELOG},
            "exactly one inserted ## heading",
            id="no-heading",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": "intro\n" + CHANGELOG},
            "not the first non-blank inserted line",
            id="intro-before-heading",
        ),
        pytest.param(
            {"CHANGELOG.md": BASE_CHANGELOG.replace("v0.38.68", "v0.38.69")},
            {"CHANGELOG.md": SECTION + BASE_CHANGELOG.replace("v0.38.68", "v0.38.69")},
            "already has a heading at the merge base",
            id="already-released",
        ),
        pytest.param(
            {},
            {"pyproject.toml": PROJECT + '\n[project.scripts]\nx = "x:main"\n'},
            "manifests are not dependency-pin-only",
            id="non-pin-manifest-key",
        ),
        pytest.param(
            {},
            {"pyproject.toml": None},
            "manifest content is missing",
            id="deleted-project",
        ),
        pytest.param(
            {"pyproject.toml": None},
            {},
            "root pyproject.toml is unreadable",
            id="absent-project",
        ),
        pytest.param(
            {"pyproject.toml": "not TOML"},
            {},
            "does not parse at the head",
            id="malformed-project",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": CHANGELOG.replace("(2026-10-08)", "(2026-1-08)")},
            "heading must match",
            id="malformed-date",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": None},
            "CHANGELOG.md is unreadable at the head",
            id="deleted-changelog",
        ),
    ],
)
def test_writer_release_cut_fails_closed(
    tmp_path: Path,
    base_changes: dict[str, str | None],
    head_changes: dict[str, str | None],
    reason: str,
) -> None:
    env = _prepare(tmp_path, base_changes, head_changes)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_writer_release_cut_requires_the_writer_app_author() -> None:
    assert (
        "steps.bot_exempt.outputs.writer_app == 'true'"
        in _step("writer_pin_only")["if"]
    )


# OMN-25958: a repository that removed its root CHANGELOG.md gets release pull
# requests from the train that change no file (omnimarket#6577, 0.4.325, 0 changed
# files), with the notes in the pull request body. Measured refusal before this
# change, dod-verify job 136997266672: "release cut requires root CHANGELOG.md".
NO_CHANGELOG: dict[str, str | None] = {"CHANGELOG.md": None}
FREE_TITLE = "chore: release x 0.38.69 (OMN-18595)"
# Fullwidth digits: Python's \d accepts them, the release tag pattern does not.
WIDE_VERSION = ".".join(chr(0xFF10 + digit) for digit in (1, 2, 3))
TITLE_SHAPE = "changelog-free release cut title must be 'chore: release <repo> <X.Y.Z> (OMN-18595)'"


def _probe_files(env: dict[str, str]) -> set[str]:
    """Return file names in the single writer-pin-only directory under dod."""
    (probe,) = (Path(env["RUNNER_TEMP"]) / "dod").glob("writer-pin-only.*")
    return {entry.name for entry in probe.iterdir() if entry.is_file()}


def _empty_release(
    tmp_path: Path, base_changes: dict[str, str | None]
) -> tuple[dict[str, str], Path]:
    env = _prepare(tmp_path, base_changes, NO_CHANGELOG, allow_empty=True)
    env["PR_TITLE"] = FREE_TITLE
    return env, Path(env["GITHUB_WORKSPACE"]) / ".dod-verify/head_home/x"


def test_writer_changelog_free_release_cut_exempts_an_empty_release(
    tmp_path: Path,
) -> None:
    env, _ = _empty_release(tmp_path, NO_CHANGELOG)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "OCC writer app authored a release cut" in result.stdout
    assert f"at {env['HEAD_SHA']}" in result.stdout
    assert f"merge base {env['BASE_SHA']}" in result.stdout
    assert "changelog-free release cut 0.38.69" in result.stdout


@pytest.mark.parametrize(
    ("base_changes", "head_changes", "empty", "title", "reason"),
    [
        pytest.param(
            NO_CHANGELOG,
            NO_CHANGELOG,
            True,
            "fix: x (OMN-18595)",
            TITLE_SHAPE,
            id="not-a-release-title",
        ),
        pytest.param(
            NO_CHANGELOG, NO_CHANGELOG, True, None, TITLE_SHAPE, id="no-title"
        ),
        pytest.param(
            {
                **NO_CHANGELOG,
                "pyproject.toml": PROJECT.replace("0.38.69", WIDE_VERSION),
            },
            NO_CHANGELOG,
            True,
            f"chore: release x {WIDE_VERSION} (OMN-18595)",
            TITLE_SHAPE,
            id="non-ascii-version-digits",
        ),
        pytest.param(
            NO_CHANGELOG,
            NO_CHANGELOG,
            True,
            "chore: release y 0.38.69 (OMN-18595)",
            "changelog-free release cut title names another repository",
            id="other-repository",
        ),
        pytest.param(
            NO_CHANGELOG,
            NO_CHANGELOG,
            True,
            "chore: release x 0.38.70 (OMN-18595)",
            "changelog-free release cut title version does not match head project.version",
            id="version-mismatch",
        ),
        pytest.param(
            {},
            {"CHANGELOG.md": BASE_CHANGELOG},
            True,
            FREE_TITLE,
            "changelog-free release cut: the merge base has a root CHANGELOG.md",
            id="base-keeps-changelog",
        ),
        pytest.param(
            NO_CHANGELOG,
            {**NO_CHANGELOG, "src/x.py": "x = 1\n"},
            False,
            FREE_TITLE,
            "changelog-free release cut requires an empty diff",
            id="source-path",
        ),
        pytest.param(
            NO_CHANGELOG,
            {**NO_CHANGELOG, "pyproject.toml": PROJECT + "\n[tool.x]\ny = 1\n"},
            False,
            FREE_TITLE,
            "changelog-free release cut requires an empty diff",
            id="non-pin-manifest-key",
        ),
        pytest.param(
            {**NO_CHANGELOG, "pyproject.toml": None},
            NO_CHANGELOG,
            True,
            FREE_TITLE,
            "changelog-free release cut root pyproject.toml is unreadable at the head",
            id="absent-head-project",
        ),
        pytest.param(
            {**NO_CHANGELOG, "pyproject.toml": "[project\n"},
            NO_CHANGELOG,
            True,
            FREE_TITLE,
            "changelog-free release cut root pyproject.toml does not parse at the head",
            id="malformed-head-project",
        ),
        pytest.param(
            {
                **NO_CHANGELOG,
                "pyproject.toml": '[project]\rname = "x"\rversion = "0.38.69"\r',
            },
            NO_CHANGELOG,
            True,
            FREE_TITLE,
            "changelog-free release cut root pyproject.toml does not parse at the head",
            id="bare-carriage-return-project",
        ),
    ],
)
def test_writer_changelog_free_release_cut_fails_closed(
    tmp_path: Path,
    base_changes: dict[str, str | None],
    head_changes: dict[str, str | None],
    empty: bool,
    title: str | None,
    reason: str,
) -> None:
    env = _prepare(tmp_path, base_changes, head_changes, allow_empty=empty)
    if title is not None:
        env["PR_TITLE"] = title
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_writer_changelog_free_release_cut_compares_trees_not_the_path_list(
    tmp_path: Path,
) -> None:
    # A submodule whose .gitmodules entry says ignore = all drops out of
    # git diff --name-only, so moving its pointer leaves an empty path list.
    gitmodules = '[submodule "sub"]\n\tpath = sub\n\turl = ./sub\n\tignore = all\n'
    env, repo = _empty_release(tmp_path, {**NO_CHANGELOG, ".gitmodules": gitmodules})
    for name, pointer in (("BASE_SHA", env["BASE_SHA"]), ("HEAD_SHA", env["HEAD_SHA"])):
        _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{pointer},sub")
        _git(repo, "commit", "-m", f"sub at {pointer}")
        env[name] = _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "diff", "--name-only", env["BASE_SHA"], env["HEAD_SHA"]) == ""
    result = _run(env)
    _assert_output(env, exempt=False)
    assert (
        "changelog-free release cut: the head tree differs from the merge base tree"
        in result.stdout
    )


def test_writer_changelog_free_release_cut_reads_only_a_regular_project_file(
    tmp_path: Path,
) -> None:
    # A symlink's blob is its target path; a target that reads as TOML must not
    # stand in for the project manifest.
    env, repo = _empty_release(tmp_path, {**NO_CHANGELOG, "pyproject.toml": None})
    (repo / "pyproject.toml").unlink(missing_ok=True)
    (repo / "pyproject.toml").symlink_to('[project]\nversion = "0.38.69"\n')
    _git(repo, "add", "pyproject.toml")
    _git(repo, "commit", "-m", "manifest as a symlink")
    env["BASE_SHA"] = _git(repo, "rev-parse", "HEAD")
    _git(repo, "commit", "--allow-empty", "-m", "empty release")
    env["HEAD_SHA"] = _git(repo, "rev-parse", "HEAD")
    result = _run(env)
    _assert_output(env, exempt=False)
    assert (
        "changelog-free release cut root pyproject.toml is not a regular file at the head"
        in result.stdout
    )
    # The step never reads the symlink's blob as the manifest.
    assert "free-project-head" not in _probe_files(env)


def test_writer_changelog_free_release_cut_needs_a_unique_merge_base(
    tmp_path: Path,
) -> None:
    # Criss-cross history: the base and the head each merge the same two
    # commits, so they have two best common ancestors. Git picks one of them, and
    # a head whose tree equals that one can still drop what the other brought.
    # Both ancestors carry the head's tree here, so the refusal cannot depend on
    # which one git picks.
    env, repo = _empty_release(tmp_path, NO_CHANGELOG)
    start = env["BASE_SHA"]
    sides = {}
    for side in ("left", "right"):
        _git(repo, "checkout", "-q", "-f", "--detach", start)
        _git(repo, "commit", "-q", "--allow-empty", "-m", side)
        sides[side] = _git(repo, "rev-parse", "HEAD")
    merges = []
    for first, second in (("left", "right"), ("right", "left")):
        _git(repo, "checkout", "-q", "-f", "--detach", sides[first])
        _git(
            repo,
            "merge",
            "-q",
            "--no-ff",
            "-m",
            f"{first} with {second}",
            sides[second],
        )
        merges.append(_git(repo, "rev-parse", "HEAD"))
    env["BASE_SHA"], env["HEAD_SHA"] = merges
    bases = _git(repo, "merge-base", "--all", env["BASE_SHA"], env["HEAD_SHA"]).split()
    assert sorted(bases) == sorted(sides.values())
    head_tree = _git(repo, "rev-parse", f"{env['HEAD_SHA']}^{{tree}}")
    assert {_git(repo, "rev-parse", f"{base}^{{tree}}") for base in bases} == {
        head_tree
    }
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "changelog-free release cut: the merge base is not unique" in result.stdout


def test_writer_pin_only_change_is_not_held_up_by_an_unreadable_root_manifest(
    tmp_path: Path,
) -> None:
    # The changelog-free probe reads the root manifest only for an empty release.
    # A pin-only change in a repository whose root pyproject.toml entry is a
    # gitlink to a commit it does not have stays exempt, as it is on dev.
    env = _prepare(
        tmp_path,
        {**NO_CHANGELOG, "pyproject.toml": None},
        NO_CHANGELOG,
        allow_empty=True,
    )
    repo = Path(env["GITHUB_WORKSPACE"]) / ".dod-verify/head_home/x"
    (repo / "pyproject.toml").unlink(missing_ok=True)
    _git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{'1' * 40},pyproject.toml",
    )
    _git(repo, "commit", "-q", "-m", "manifest as a gitlink")
    env["BASE_SHA"] = _git(repo, "rev-parse", "HEAD")
    (repo / "uv.lock").write_text('version = "0.38.69"\nrevision = 2\n')
    _git(repo, "add", "uv.lock")
    _git(repo, "commit", "-q", "-m", "lockfile pin")
    env["HEAD_SHA"] = _git(repo, "rev-parse", "HEAD")
    env["PR_TITLE"] = FREE_TITLE
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "dependency-pin-only" in result.stdout
    # A non-empty diff is never probed by the changelog-free step.
    assert not {
        "changelog-at-base-tree",
        "merge-bases",
        "trees-identical",
    } & _probe_files(env)
