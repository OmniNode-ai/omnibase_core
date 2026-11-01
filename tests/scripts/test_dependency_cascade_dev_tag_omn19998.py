# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19998: the dependency cascade writes dev merge tags, never release pins.

RULING 2026-10-29T01:50:26Z (OMN-21433): first-party dependencies iterate on
dev merge tags (``dev-<UTC YYYYMMDDHHMMSS>-<sha12>``), not on releases. The
cascade used to wait for the RELEASED version on the index and write an exact
``==X.Y.Z`` pin or a registry lock entry, which the downstream
``internal-sibling-pins`` job refuses where the package already carries a newer
dev merge tag (OMN-21282). It now resolves the newest dev merge tag of the
package from its own tags and writes the same source pin the downstream
provenance gates accept:

    <pkg> = { git = "https://github.com/OmniNode-ai/<repo>.git", tag = "<dev tag>" }

These tests parse the workflow and execute the real Bash and Python of the
steps that decide the pin, against stubs for ``git`` and ``uv``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"

_JOB_NAME = "open-bump-pr"
_VARS_STEP = "Set branch and PR variables"
_PIN_STEP = "Pin dev merge tag source (OMN-19998)"
_LOCK_STEP = "Upgrade lockfile"
_VERIFY_STEP = "Verify locked source is the target dev tag (OMN-19998)"

# What GitHub sets in every step of a run on the org's repositories.
_RUN_CONTEXT = {
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY_OWNER": "OmniNode-ai",
}
_SOURCE_URL = "/".join((*_RUN_CONTEXT.values(), "omnibase_core.git"))

_DEV_TAG_RE = re.compile(r"^dev-[0-9]{14}-[0-9a-f]{12}$")
_NEWEST_TAG = "dev-20261101175705-134f715a53e5"
_NEWEST_SHA = "134f715a53e5" + "0" * 28
_OLDER_TAG = "dev-20261101152344-a22c8c0a1df0"
_OLDER_SHA = "a22c8c0a1df0" + "0" * 28


def _document() -> dict[object, object]:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    assert isinstance(document, dict)
    return document


def _steps() -> list[dict[str, object]]:
    jobs = _document()["jobs"]
    assert isinstance(jobs, dict)
    steps = jobs[_JOB_NAME]["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(
        f"job {_JOB_NAME!r} has no step named {name!r}; steps present: "
        f"{[s.get('name') for s in _steps()]}"
    )


def _run_text(name: str) -> str:
    run = _step(name).get("run")
    assert isinstance(run, str), name
    return run


def _bash(
    tmp_path: Path,
    script_text: str,
    env: dict[str, str],
    cwd: Path,
    bin_dir: Path,
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "step.sh"
    script.write_text(script_text)
    args = [f"{key}={value}" for key, value in env.items()]
    return subprocess.run(
        [
            "env",
            f"PATH={bin_dir}:/usr/bin:/bin",
            *args,
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            str(script),
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _bin_with_stubs(tmp_path: Path, *, ls_remote: str | None = None) -> Path:
    """A PATH directory holding a ``git`` stub (ls-remote) and a ``uv`` shim.

    The ``uv`` shim turns ``uv run --no-project [--with X] python ...`` into the
    interpreter running this test, so the step's Python runs for real.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(
        "#!/bin/bash\nset -eu\n"
        'if [ "$1" = run ] && [ "$2" = --no-project ]; then\n'
        "  shift 2\n"
        '  while [ "$1" != python ]; do shift; done\n'
        "  shift\n"
        f'  exec "{sys.executable}" "$@"\n'
        "fi\n"
        'echo "unexpected uv call: $*" >&2\n'
        "exit 99\n"
    )
    (bin_dir / "uv").chmod(0o755)
    if ls_remote is not None:
        (tmp_path / "ls-remote.out").write_text(ls_remote)
        (bin_dir / "git").write_text(
            "#!/bin/bash\nset -eu\n"
            'printf "%s\\n" "$*" >> "$STUB_STATE/git-argv"\n'
            'if [ "${LS_REMOTE_FAIL:-}" = 1 ]; then echo "fatal: unable to access" >&2; exit 128; fi\n'
            'cat "$STUB_STATE/ls-remote.out"\n'
        )
        (bin_dir / "git").chmod(0o755)
    return bin_dir


# --------------------------------------------------------------- tag resolution


def _ls_remote(*refs: tuple[str, str]) -> str:
    return "".join(f"{sha}\trefs/tags/{name}\n" for sha, name in refs)


def _run_vars(
    tmp_path: Path, ls_remote: str, **overrides: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    work = tmp_path / "work"
    work.mkdir()
    out = tmp_path / "github-output"
    out.touch()
    env = {
        "RAW_VERSION": "v0.47.61",
        "RAW_PACKAGE": "omnibase_core",
        "RAW_TICKET": "OMN-19998",
        "RAW_EVIDENCE_SOURCE": "",
        "GIT_SOURCE_TOKEN": "",
        "GIT_SOURCE_REPOS": "",
        "GITHUB_OUTPUT": str(out),
        "STUB_STATE": str(tmp_path),
        **_RUN_CONTEXT,
    }
    env.update(overrides)
    result = _bash(
        tmp_path,
        _run_text(_VARS_STEP),
        env,
        work,
        _bin_with_stubs(tmp_path, ls_remote=ls_remote),
    )
    outputs = dict(
        line.split("=", 1) for line in out.read_text().splitlines() if "=" in line
    )
    return result, outputs


@pytest.mark.unit
def test_resolves_the_newest_dev_merge_tag_not_the_release(tmp_path: Path) -> None:
    refs = _ls_remote(
        ("1" * 40, "v0.47.61"),
        (_OLDER_SHA, _OLDER_TAG),
        (_NEWEST_SHA, _NEWEST_TAG),
        ("2" * 40, "dev-not-a-merge-tag"),
        ("3" * 40, "dev-20261101999999-zzzzzzzzzzzz"),
    )
    result, outputs = _run_vars(tmp_path, refs)
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs["version"] == _NEWEST_TAG, outputs
    assert outputs["tag_sha"] == _NEWEST_SHA, outputs
    assert _DEV_TAG_RE.match(outputs["version"])
    assert outputs["branch"] == (
        f"automation/bump-omnibase-core-{_NEWEST_TAG}-omn-19998"
    ), outputs


@pytest.mark.unit
def test_prefers_the_peeled_commit_of_an_annotated_tag(tmp_path: Path) -> None:
    refs = _ls_remote(("9" * 40, _NEWEST_TAG), (_NEWEST_SHA, f"{_NEWEST_TAG}^{{}}"))
    result, outputs = _run_vars(tmp_path, refs)
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs["tag_sha"] == _NEWEST_SHA, outputs


@pytest.mark.unit
def test_a_release_only_tag_list_fails_the_leg(tmp_path: Path) -> None:
    result, _ = _run_vars(tmp_path, _ls_remote(("1" * 40, "v0.47.61")))
    assert result.returncode != 0
    assert "dev merge tag" in result.stdout + result.stderr


@pytest.mark.unit
def test_a_tag_whose_sha_suffix_disagrees_with_its_commit_fails(
    tmp_path: Path,
) -> None:
    result, _ = _run_vars(tmp_path, _ls_remote(("f" * 40, _NEWEST_TAG)))
    assert result.returncode != 0
    assert "does not match" in result.stdout + result.stderr


@pytest.mark.unit
def test_an_unreadable_tag_list_fails_the_leg(tmp_path: Path) -> None:
    result, _ = _run_vars(
        tmp_path, _ls_remote((_NEWEST_SHA, _NEWEST_TAG)), LS_REMOTE_FAIL="1"
    )
    assert result.returncode != 0


@pytest.mark.unit
def test_a_release_version_input_is_optional_and_never_the_pin(
    tmp_path: Path,
) -> None:
    result, outputs = _run_vars(
        tmp_path, _ls_remote((_NEWEST_SHA, _NEWEST_TAG)), RAW_VERSION=""
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs["version"] == _NEWEST_TAG
    for name in ("workflow_call", "workflow_dispatch"):
        on = _document()[True]  # PyYAML reads the bare `on` key as boolean True
        assert isinstance(on, dict)
        version = on[name]["inputs"]["version"]
        assert version.get("required") is False, (name, version)


@pytest.mark.unit
def test_a_malformed_release_version_input_is_still_refused(tmp_path: Path) -> None:
    result, _ = _run_vars(
        tmp_path, _ls_remote((_NEWEST_SHA, _NEWEST_TAG)), RAW_VERSION="x; rm -rf /"
    )
    assert result.returncode != 0


@pytest.mark.unit
def test_a_private_package_repo_is_read_with_the_scoped_token(tmp_path: Path) -> None:
    result, _ = _run_vars(
        tmp_path,
        _ls_remote((_NEWEST_SHA, _NEWEST_TAG)),
        GIT_SOURCE_TOKEN=uuid.uuid4().hex,
        GIT_SOURCE_REPOS="omnibase_core",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    argv = (tmp_path / "git-argv").read_text()
    assert "ls-remote" in argv and "refs/tags/dev-*" in argv, argv
    assert "extraheader" in argv, argv


# ------------------------------------------------------------- the source pin


_OTHER_REV = "9" * 40
_OMNICLAUDE_LIKE = f"""\
[project]
name = "downstream"
version = "0.1.0"
dependencies = [
    "omnibase-core>=0.47.0,<0.48.0",
    "omnibase-spi>=0.23.1,<0.24.0",
]

[tool.uv.sources]
# omnibase-core resolves from PyPI today.
omninode-intelligence = {{ git = "https://github.com/OmniNode-ai/omniintelligence.git", rev = "{_OTHER_REV}" }}
"""


def _run_pin(
    tmp_path: Path, pyproject: str, tag: str = _NEWEST_TAG
) -> tuple[subprocess.CompletedProcess[str], str]:
    work = tmp_path / "work"
    work.mkdir()
    (work / "pyproject.toml").write_text(pyproject)
    result = _bash(
        tmp_path,
        _run_text(_PIN_STEP),
        {
            "PKG_HYPHEN": "omnibase-core",
            "PACKAGE": "omnibase_core",
            "DEV_TAG": tag,
            **_RUN_CONTEXT,
        },
        work,
        _bin_with_stubs(tmp_path),
    )
    return result, (work / "pyproject.toml").read_text()


def _source(text: str, name: str = "omnibase-core") -> dict[str, object]:
    sources = tomllib.loads(text)["tool"]["uv"]["sources"]
    assert isinstance(sources, dict)
    entry = sources[name]
    assert isinstance(entry, dict)
    return entry


@pytest.mark.unit
def test_pin_step_adds_the_dev_tag_source_the_provenance_gates_accept(
    tmp_path: Path,
) -> None:
    result, text = _run_pin(tmp_path, _OMNICLAUDE_LIKE)
    assert result.returncode == 0, result.stdout + result.stderr
    # Exactly the two keys omniclaude's check_dep_provenance exempts (OMN-19998).
    assert _source(text) == {
        "git": _SOURCE_URL,
        "tag": _NEWEST_TAG,
    }
    assert _DEV_TAG_RE.match(str(_source(text)["tag"]))
    # The range, the other sibling's pin and the other source are untouched.
    assert '"omnibase-core>=0.47.0,<0.48.0"' in text
    assert _OTHER_REV in text
    assert "==" not in text


@pytest.mark.unit
def test_pin_step_moves_an_older_dev_tag_forward_in_place(tmp_path: Path) -> None:
    older = _OMNICLAUDE_LIKE + (
        f'omnibase-core = {{ git = "{_SOURCE_URL}",'
        f' tag = "{_OLDER_TAG}" }}  # moved by the train\n'
    )
    result, text = _run_pin(tmp_path, older)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _source(text)["tag"] == _NEWEST_TAG
    assert text.count("omnibase-core = {") == 1
    assert _OLDER_TAG not in text


@pytest.mark.unit
def test_pin_step_replaces_a_stale_rev_or_release_tag_source(tmp_path: Path) -> None:
    stale = _OMNICLAUDE_LIKE + (
        f'omnibase_core = {{ git = "{_SOURCE_URL}", tag = "v0.47.58" }}\n'
    )
    result, text = _run_pin(tmp_path, stale)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _source(text)["tag"] == _NEWEST_TAG
    assert "v0.47.58" not in text


@pytest.mark.unit
def test_pin_step_creates_the_sources_table_when_the_repo_has_none(
    tmp_path: Path,
) -> None:
    bare = (
        '[project]\nname = "x"\nversion = "0"\n'
        'dependencies = ["omnibase-core>=0.47.5,<0.48.0"]\n'
    )
    result, text = _run_pin(tmp_path, bare)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _source(text)["tag"] == _NEWEST_TAG


@pytest.mark.unit
def test_pin_step_turns_an_exact_release_pin_into_a_range_never_a_new_exact_pin(
    tmp_path: Path,
) -> None:
    exact = _OMNICLAUDE_LIKE.replace(
        '"omnibase-core>=0.47.0,<0.48.0"', '"omnibase-core==0.46.8"'
    )
    result, text = _run_pin(tmp_path, exact)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "omnibase-core==" not in text
    assert '"omnibase-core>=0.46.8,<0.47.0"' in text
    assert _source(text)["tag"] == _NEWEST_TAG


@pytest.mark.unit
def test_pin_step_refuses_a_malformed_tag(tmp_path: Path) -> None:
    result, text = _run_pin(tmp_path, _OMNICLAUDE_LIKE, tag="v0.47.61")
    assert result.returncode != 0
    assert text == _OMNICLAUDE_LIKE


@pytest.mark.unit
def test_pin_step_refuses_a_package_table_it_cannot_rewrite(tmp_path: Path) -> None:
    sub = _OMNICLAUDE_LIKE + '\n[tool.uv.sources.omnibase-core]\ngit = "x"\ntag = "y"\n'
    result, text = _run_pin(tmp_path, sub)
    assert result.returncode != 0
    assert text == sub


# ------------------------------------------------------ verification of the lock


def _lock(source: str, version: str = "0.47.62") -> str:
    return (
        "version = 1\n\n[[package]]\n"
        f'name = "omnibase-core"\nversion = "{version}"\nsource = {source}\n'
    )


def _run_verify(tmp_path: Path, lock_text: str) -> subprocess.CompletedProcess[str]:
    work = tmp_path / "work"
    work.mkdir()
    (work / "uv.lock").write_text(lock_text)
    return _bash(
        tmp_path,
        _run_text(_VERIFY_STEP),
        {
            "PKG_HYPHEN": "omnibase-core",
            "PACKAGE": "omnibase_core",
            "DEV_TAG": _NEWEST_TAG,
            "TAG_SHA": _NEWEST_SHA,
            "REPO_NAME": "omniclaude",
            **_RUN_CONTEXT,
        },
        work,
        _bin_with_stubs(tmp_path),
    )


@pytest.mark.unit
def test_verify_step_passes_a_lock_that_records_the_dev_tag(tmp_path: Path) -> None:
    source = f'{{ git = "{_SOURCE_URL}?tag={_NEWEST_TAG}#{_NEWEST_SHA}" }}'
    result = _run_verify(tmp_path, _lock(source))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.unit
def test_verify_step_fails_a_lock_still_on_a_registry_release(tmp_path: Path) -> None:
    result = _run_verify(
        tmp_path, _lock('{ registry = "https://pypi.org/simple" }', "0.47.61")
    )
    assert result.returncode != 0
    assert "CASCADE-LOCKED-SOURCE-MISMATCH" in result.stdout


@pytest.mark.unit
def test_verify_step_fails_a_lock_on_an_older_dev_tag(tmp_path: Path) -> None:
    source = f'{{ git = "{_SOURCE_URL}?tag={_OLDER_TAG}#{_OLDER_SHA}" }}'
    result = _run_verify(tmp_path, _lock(source))
    assert result.returncode != 0


# ------------------------------------------- AC3: no second, release-pin producer


@pytest.mark.unit
def test_no_step_writes_an_exact_release_pin_or_waits_for_the_index() -> None:
    names = [s.get("name") for s in _steps()]
    assert not any("released version" in str(n).lower() for n in names), names
    assert "Check dependency is movable" not in names, names
    pin_write = re.compile(r"==\s*(\$\{?(RESOLVED|VERSION|TARGET_VERSION)\}?|[0-9])")
    for step in _steps():
        run = step.get("run")
        if not isinstance(run, str):
            continue
        assert not pin_write.search(run), (step.get("name"), run)
        assert "pypi.org/simple/" not in run, (step.get("name"), run)
        assert (
            "--upgrade-package" not in run
            or "==" not in run.split("--upgrade-package", 1)[1].split("\n", 1)[0]
        ), (step.get("name"), run)


@pytest.mark.unit
def test_every_step_that_pins_pins_a_dev_tag() -> None:
    pin = _run_text(_PIN_STEP)
    assert "DEV_TAG" in pin and "tag" in pin
    lock = _run_text(_LOCK_STEP)
    assert "uv lock" in lock
    names = [s.get("name") for s in _steps()]
    assert names.index(_VARS_STEP) < names.index(_PIN_STEP) < names.index(_LOCK_STEP)
    assert names.index(_LOCK_STEP) < names.index(_VERIFY_STEP)
    assert names.index(_VERIFY_STEP) < names.index("Commit and push")


@pytest.mark.unit
def test_the_commit_and_pr_text_speak_of_a_dev_tag_not_a_release() -> None:
    commit = _run_text("Commit and push")
    assert "release ${RESOLVED}" not in commit, commit
    body = _run_text("Open pull request")
    assert "(==X.Y.Z)" not in body, body
    assert "dev merge tag" in body, body


@pytest.mark.unit
def test_skip_summary_states_the_locked_dev_tag_not_a_release() -> None:
    run = _run_text("Skip summary")
    assert "the released version" not in run, run
    assert "dev merge tag" in run, run
    assert "already on latest" not in _run_text(_LOCK_STEP)


@pytest.mark.unit
def test_verify_step_runs_on_a_skipped_leg_with_the_tag_and_commit() -> None:
    step = _step(_VERIFY_STEP)
    assert step.get("if") == "steps.token_check.outputs.has_token == 'true'", step
    env = step.get("env")
    assert isinstance(env, dict)
    assert env.get("DEV_TAG") == "${{ steps.vars.outputs.version }}", env
    assert env.get("TAG_SHA") == "${{ steps.vars.outputs.tag_sha }}", env
    names = [s.get("name") for s in _steps()]
    assert names.index(_VERIFY_STEP) < names.index("Skip summary")


@pytest.mark.unit
def test_the_cascade_opens_prs_and_never_closes_or_merges_them() -> None:
    """The stale release-pin bump PRs are closed by their owners, not here."""
    for step in _steps():
        run = step.get("run")
        if isinstance(run, str):
            assert not re.search(r"gh pr (close|merge|edit|ready)", run), step.get(
                "name"
            )
