# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Executable pins for the job-local writer-app pin-only verdict (OMN-17427).

Extract the dod-verify steps from YAML and run them under bash with controlled
GitHub metadata, a real git history, and a pinned-verifier launcher stub.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.ci.test_bot_exempt_writer_app_pin_only_omn20161 import _run as _run_bot

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
GUARD = (
    "steps.bot_exempt.outputs.exempt != 'true' "
    "&& steps.same_repo.outcome != 'failure' "
    "&& steps.tickets.outcome != 'failure'"
)
BASE_PROJECT = '[project]\nname = "x"\nversion = "0.1.0"\n'
HEAD_PROJECT = '[project]\nname = "x"\nversion = "0.1.1"\n'


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _steps() -> list[dict[str, Any]]:
    return _workflow()["jobs"]["dod-verify"]["steps"]


def _step(step_id: str) -> dict[str, Any]:
    return next(step for step in _steps() if step.get("id") == step_id)


@pytest.mark.parametrize(
    ("login", "probe_exit", "exempt", "writer_app"),
    [
        (login, code, code == 0, code != 0)
        for login in (
            "onexbot-occ-writer[bot]",
            "app/onexbot-occ-writer",
            "onexbot-occ-writer",
        )
        for code in (0, 1)
    ]
    + [("jonah", 1, False, False), ("dependabot[bot]", 1, True, False)],
)
def test_bot_exempt_marks_an_unproven_writer_app(
    tmp_path: Path, login: str, probe_exit: int, exempt: bool, writer_app: bool
) -> None:
    line, _ = _run_bot(
        tmp_path,
        "receipt-gate-dod-verify",
        author=login,
        probe="in-tree",
        probe_exit=probe_exit,
    )
    assert line == f"exempt={str(exempt).lower()}"
    assert (tmp_path / "github_output.txt").read_text().splitlines() == [
        line,
        f"writer_app={str(writer_app).lower()}",
    ]


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
        },
    )
    return result.stdout.strip()


def _prepare(
    tmp_path: Path, *, extra_paths: tuple[str, ...] = ()
) -> tuple[dict[str, str], Path]:
    workspace = tmp_path / "ws"
    repo = workspace / ".dod-verify" / "head_home" / "x"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "pyproject.toml").write_text(BASE_PROJECT)
    (repo / "uv.lock").write_text('version = "0.1.0"\n')
    for path in extra_paths:
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(BASE_PROJECT if file.name == "pyproject.toml" else "base\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "pyproject.toml").write_text(HEAD_PROJECT)
    (repo / "uv.lock").write_text('version = "0.1.1"\n')
    for path in extra_paths:
        file = repo / path
        file.write_text(HEAD_PROJECT if file.name == "pyproject.toml" else "head\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    runner = tmp_path / "runner"
    runner.mkdir()
    stub = tmp_path / "stub"
    package = stub / "omnimarket"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    record = tmp_path / "classifier.json"
    (package / "occ_content_probe.py").write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "def classify_dependency_pin_only(changed_paths, *, pyproject_head, pyproject_base):\n"
        "    Path(os.environ['CLASSIFIER_RECORD']).write_text(json.dumps({\n"
        "        'paths': changed_paths, 'head': pyproject_head, 'base': pyproject_base,\n"
        "        'cwd': os.getcwd(), 'isolated': sys.flags.isolated}))\n"
        "    if set(changed_paths) == {'pyproject.toml', 'uv.lock'} and pyproject_head and pyproject_base:\n"
        "        return True, 'version/dependency-pin keys only: project.version'\n"
        "    return False, 'paths or manifest contents are not pin-only'\n"
    )
    launcher = tmp_path / "verifier"
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "sys.argv = ['-', *sys.argv[2:]]; "
        "exec(compile(sys.stdin.read(), '<stdin>', 'exec'))"
    )
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
        "CLASSIFIER_RECORD": str(record),
    }, record


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", "-c", _step("writer_pin_only")["run"]],
        env=env,
        cwd=env["GITHUB_WORKSPACE"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _assert_output(env: dict[str, str], *, exempt: bool) -> None:
    assert Path(env["GITHUB_OUTPUT"]).read_text().splitlines() == [
        f"exempt={str(exempt).lower()}"
    ]


def test_writer_pin_only_step_exempts_a_version_bump(tmp_path: Path) -> None:
    env, record = _prepare(tmp_path)
    # Working-tree edits cannot supply the classifier's content or imports.
    repo = Path(env["GITHUB_WORKSPACE"]) / ".dod-verify/head_home/x"
    (repo / "pyproject.toml").write_text("malformed TOML in the working tree")
    result = _run(env)
    _assert_output(env, exempt=True)
    assert json.loads(record.read_text()) == {
        "paths": ["pyproject.toml", "uv.lock"],
        "head": HEAD_PROJECT,
        "base": BASE_PROJECT,
        "cwd": env["RUNNER_TEMP"],
        "isolated": 1,
    }
    assert f"at {env['HEAD_SHA']}" in result.stdout
    assert f"merge base {env['BASE_SHA']}" in result.stdout
    assert "version/dependency-pin keys only: project.version" in result.stdout


def test_writer_pin_only_step_refuses_a_source_change(tmp_path: Path) -> None:
    env, record = _prepare(tmp_path, extra_paths=("src/x.py",))
    result = _run(env)
    _assert_output(env, exempt=False)
    assert json.loads(record.read_text())["paths"] == [
        "pyproject.toml",
        "src/x.py",
        "uv.lock",
    ]
    assert "paths or manifest contents are not pin-only" in result.stdout


def test_writer_pin_only_step_refuses_two_manifests_without_calling_the_classifier(
    tmp_path: Path,
) -> None:
    env, record = _prepare(tmp_path, extra_paths=("other/pyproject.toml",))
    result = _run(env)
    _assert_output(env, exempt=False)
    assert not record.exists()
    assert "more than one dependency manifest changed" in result.stdout


@pytest.mark.parametrize("broken", ["exit 1", "echo not-JSON", "missing"])
def test_writer_pin_only_step_fails_closed_on_a_broken_verifier(
    tmp_path: Path, broken: str
) -> None:
    env, record = _prepare(tmp_path)
    launcher = Path(env["DOD_VERIFY_PY"])
    if broken == "missing":
        del env["DOD_VERIFY_PY"]
    else:
        launcher.write_text(f"#!/bin/bash\n{broken}\n")
    result = _run(env)
    _assert_output(env, exempt=False)
    assert not record.exists()
    assert "::notice::OCC writer app is not exempt:" in result.stdout


def test_writer_pin_only_step_is_gated_and_gates_every_evidence_step() -> None:
    ids = [step.get("id") for step in _steps()]
    index = ids.index("writer_pin_only")
    assert ids[index - 1 : index + 2] == ["verifier", "writer_pin_only", "pg_tools"]
    step = _step("writer_pin_only")
    assert step["if"] == GUARD + " && steps.bot_exempt.outputs.writer_app == 'true'"
    assert step["continue-on-error"] == "${{ inputs.shadow == 'true' }}"
    assert step["env"] == {
        "REPO_SHORT": "${{ github.event.repository.name }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
    }
    assert 'cd "$RUNNER_TEMP" && "$DOD_VERIFY_PY" -I - ' in step["run"]
    for step_id in (
        "pg_tools",
        "pg_env",
        "head_verify",
        "merge_base",
        "base_control",
        "occ_difference",
    ):
        assert "steps.writer_pin_only.outputs.exempt != 'true'" in _step(step_id)["if"]
    assert not any(
        step.get("id") == "writer_pin_only"
        for step in _workflow()["jobs"]["verify"]["steps"]
    )


@pytest.mark.parametrize("shadow", ["true", "false"])
def test_shadow_summary_counts_the_writer_pin_only_exemption(
    tmp_path: Path, shadow: str
) -> None:
    step = next(step for step in _steps() if step["name"] == "Summarise")
    assert step["if"] == "always()"
    script = step["run"]
    assert "verifier writer_pin_only pg_tools" in script
    assert (
        "if [ \"$(jq -r '.writer_pin_only.outputs.exempt // empty' "
        '<<< "$STEPS_JSON")" = true ]; then\n      new_path=exempt'
    ) in script
    summary = tmp_path / "summary"
    result = subprocess.run(
        ["bash", "-c", script],
        env={
            "PATH": "/usr/bin:/bin",
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_STEP_SUMMARY": str(summary),
            "VERIFIER_VERSION": "0.4.280",
            "HEAD_SHA": "a" * 40,
            "SHADOW": shadow,
            "STEPS_JSON": json.dumps(
                {"writer_pin_only": {"outputs": {"exempt": "true"}}}
            ),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    text = summary.read_text()
    if shadow == "true":
        assert "new_path=exempt refused_step=none occ_difference=not_run" in text
    else:
        assert (
            "Writer-app dependency-pin-only exemption: derived at the head (OMN-17427)"
            in text.splitlines()
        )
