# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Execute the writer-app workflow checkout pin verdict against real git objects.

omnibase_core's downstream pin bump (OMN-9050) moves the 40-hex ``ref:`` of an
``actions/checkout`` step pinned to omnibase_core and nothing else. Under OCC the
occ-autobind producer classified that diff as dependency-pin-only; in caller
evidence mode the producer no longer runs, so the dod-verify writer_pin_only step
must derive the same verdict itself with the pinned verifier's
``classify_workflow_core_pin_only`` (OMN-20074).
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
)

pytestmark = pytest.mark.unit

WORKFLOW = ".github/workflows/check-handshake.yml"
OLD_SHA = "e" * 40
NEW_SHA = "2" * 40


def _handshake(sha: str) -> str:
    return (
        "jobs:\n"
        "  handshake:\n"
        "    steps:\n"
        "      - uses: actions/checkout@v7\n"
        "        with:\n"
        "          repository: OmniNode-ai/omnibase_core\n"
        f"          # Auto-bumped by omnibase_core publish-downstream-pin-bump.yml to {sha[:12]}.\n"
        f"          ref: {sha}\n"
        "          path: omnibase_core\n"
    )


# A recording stand-in for the pinned verifier's classifiers. The workflow
# classifier mirrors the real one's contract: refuse non-workflow paths and
# unreadable sides, and admit a diff whose only change is the core pin line.
PROBE = dedent("""\
    import json, os, re
    from pathlib import Path

    def is_release_artifact_only_diff(paths):
        return False

    def classify_dependency_pin_only(paths, *, pyproject_head, pyproject_base):
        return False, "changed path is not a dependency manifest or lockfile: " + paths[0]

    def classify_workflow_core_pin_only(changed_paths, *, contents):
        Path(os.environ["CLASSIFIER_RECORD"]).write_text(json.dumps(
            {"paths": list(changed_paths), "contents": contents}))
        pin = re.compile(r"^ *(# Auto-bumped .*|ref: [0-9a-f]{40})$")
        for path in changed_paths:
            if not path.startswith(".github/workflows/"):
                return False, f"changed path is not a workflow file: {path}"
            head, base = contents.get(path, (None, None))
            if head is None or base is None:
                return False, f"workflow content unreadable at one or both refs: {path}"
            strip = lambda text: [l for l in text.splitlines() if not pin.match(l)]
            if strip(head) != strip(base):
                return False, f"{path} changes outside the omnibase_core checkout pin and its banner"
        return True, "omnibase_core workflow checkout pin only -> 222222222222: " + ", ".join(changed_paths)
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
    head_changes: dict[str, str | None],
    *,
    base_changes: dict[str, str | None] | None = None,
    probe: str = PROBE,
) -> tuple[dict[str, str], Path]:
    workspace = tmp_path / "ws"
    repo = workspace / ".dod-verify/head_home/x"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _write_files(
        repo,
        {
            "pyproject.toml": '[project]\nname = "x"\nversion = "0.1.0"\n',
            WORKFLOW: _handshake(OLD_SHA),
            **(base_changes or {}),
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _write_files(repo, head_changes)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    # The verdict must come from git objects, never from the working tree.
    _write_files(repo, {WORKFLOW: "not the committed workflow\n"})
    runner = tmp_path / "runner"
    runner.mkdir()
    stub = tmp_path / "stub"
    package = stub / "omnimarket"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "occ_content_probe.py").write_text(probe)
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
    record = tmp_path / "classifier.json"
    return {
        "PATH": "/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
        "RUNNER_TEMP": str(runner),
        "REPO_SHORT": "x",
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "DOD_VERIFY_PY": str(launcher),
        "CLASSIFIER_RECORD": str(record),
    }, record


def test_writer_workflow_core_pin_bump_is_exempt(tmp_path: Path) -> None:
    env, record = _prepare(tmp_path, {WORKFLOW: _handshake(NEW_SHA)})
    result = _run(env)
    _assert_output(env, exempt=True)
    assert json.loads(record.read_text()) == {
        "paths": [WORKFLOW],
        "contents": {WORKFLOW: [_handshake(NEW_SHA), _handshake(OLD_SHA)]},
    }
    assert "OCC writer app authored a dependency-pin-only change" in result.stdout
    assert f"at {env['HEAD_SHA']}" in result.stdout
    assert f"merge base {env['BASE_SHA']}" in result.stdout
    assert "classify_workflow_core_pin_only" in result.stdout
    assert "omnibase_core workflow checkout pin only -> 222222222222" in result.stdout


@pytest.mark.parametrize(
    ("head_changes", "base_changes", "reason"),
    [
        pytest.param(
            {WORKFLOW: _handshake(NEW_SHA), "contracts/OMN-9050.yaml": "x: 1\n"},
            None,
            "changed path is not a dependency manifest or lockfile",
            id="workflow-and-contract",
        ),
        pytest.param(
            {WORKFLOW: _handshake(NEW_SHA) + "      - run: echo extra\n"},
            None,
            "changes outside the omnibase_core checkout pin",
            id="workflow-pin-and-step",
        ),
        pytest.param(
            {".github/workflows/new.yml": _handshake(NEW_SHA)},
            None,
            "workflow content unreadable at one or both refs",
            id="added-workflow",
        ),
        pytest.param(
            {WORKFLOW: None},
            None,
            "workflow content unreadable at one or both refs",
            id="deleted-workflow",
        ),
    ],
)
def test_writer_workflow_pin_fails_closed(
    tmp_path: Path,
    head_changes: dict[str, str | None],
    base_changes: dict[str, str | None] | None,
    reason: str,
) -> None:
    env, _ = _prepare(tmp_path, head_changes, base_changes=base_changes)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_writer_workflow_pin_never_reaches_the_classifier_for_a_mixed_diff(
    tmp_path: Path,
) -> None:
    env, record = _prepare(
        tmp_path, {WORKFLOW: _handshake(NEW_SHA), "src/x.py": "x = 1\n"}
    )
    _run(env)
    _assert_output(env, exempt=False)
    assert not record.exists()


def test_writer_workflow_pin_fails_closed_on_a_verifier_without_the_classifier(
    tmp_path: Path,
) -> None:
    older = PROBE.split("def classify_workflow_core_pin_only", 1)[0]
    env, _ = _prepare(tmp_path, {WORKFLOW: _handshake(NEW_SHA)}, probe=older)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert "the pinned classifier failed" in result.stdout
