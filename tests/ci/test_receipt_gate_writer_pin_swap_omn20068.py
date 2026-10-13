# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Run the OMN-20068 writer-app pin-swap verdict against real git objects."""

from __future__ import annotations

import re
import shlex
from collections.abc import Mapping
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
    _step,
)
from tests.ci.test_receipt_gate_writer_workflow_pin_omn20074 import (
    _prepare as _prepare_workflow,
)

pytestmark = pytest.mark.unit

OLD = "e" * 40
NEW = "8a" * 20
CONTRACT = ".github/omnimarket-contract-pin.yaml"
SIBLINGS = ".github/sibling-pins.yaml"
W1 = ".github/workflows/w1.yml"
EXTRA = ".github/workflows/extra.yml"
PROJECT = '[project]\nname = "x"\nversion = "0.1.0"\n'

PROBE = dedent("""\
    import re
    from pathlib import Path

    def classify_dependency_pin_only(paths, *, pyproject_head, pyproject_base):
        if not paths:
            return False, "no changed dependency paths"
        for path in paths:
            if Path(path).name not in {"pyproject.toml", "uv.lock"}:
                return False, f"not a dependency manifest or lockfile: {path}"
        if any(Path(path).name == "pyproject.toml" for path in paths):
            if pyproject_head is None or pyproject_base is None:
                return False, "unreadable project manifest"
            strip = lambda text: re.sub(r'^version = "[^"\\n]+"$', '', text, flags=re.M)
            if strip(pyproject_head) != strip(pyproject_base):
                return False, "project changes outside project.version"
        return True, "version/dependency-pin keys only: project.version"

    def is_release_artifact_only_diff(paths):
        return False

    def classify_workflow_core_pin_only(paths, *, contents):
        return False, "no omnibase_core checkout pin moved"
    """)


def _workflow(sha: str, refs: int = 1) -> str:
    steps = "".join(
        "      - uses: actions/checkout@v7\n"
        "        with:\n"
        "          repository: OmniNode-ai/omnimarket\n"
        f"          ref: {sha} # .github/sibling-pins.yaml\n"
        f"          path: checkout-{index}\n"
        for index in range(refs)
    )
    return "jobs:\n  ci:\n    steps:\n" + steps + "      - run: echo hello\n"


BASE_FILES = {
    "pyproject.toml": PROJECT,
    "uv.lock": "version = 1\n",
    CONTRACT: f"repository: OmniNode-ai/omnimarket\nomnimarket_contract_ref: {OLD}\n",
    SIBLINGS: f"pins:\n  omnibase_core: {'a' * 40}\n  omnimarket: {OLD}\n",
    **{
        # omnibase_infra#4832: ci.yml moves 5 refs, runtime-rebuild-trigger.yml
        # moves 2 and seven more workflows move 1 each.
        f".github/workflows/w{index}.yml": _workflow(OLD, {9: 5, 8: 2}.get(index, 1))
        for index in range(1, 10)
    },
    EXTRA: _workflow(OLD),
}
SWAP_FILES = {
    path: content.replace(OLD, NEW)
    for path, content in BASE_FILES.items()
    if path in {CONTRACT, SIBLINGS} or path.startswith(".github/workflows/w")
}


def _prepare(
    tmp_path: Path,
    changes: Mapping[str, str | None],
    *,
    base_changes: dict[str, str | None] | None = None,
) -> dict[str, str]:
    env, _ = _prepare_workflow(
        tmp_path,
        dict(changes),
        base_changes={**BASE_FILES, **(base_changes or {})},
        probe=PROBE,
    )
    # A dirty checkout must not influence the verdict from committed blobs.
    repo = Path(env["GITHUB_WORKSPACE"]) / ".dod-verify/head_home/x"
    (repo / W1).write_text("not the committed workflow\n")
    (repo / CONTRACT).write_text("not the committed pin file\n")
    return env


def test_4832_pin_swap_is_exempt(tmp_path: Path) -> None:
    env = _prepare(tmp_path, SWAP_FILES)
    result = _run(env)
    _assert_output(env, exempt=True)
    for expected in (
        "pin-swap-only change",
        "classify_pin_swap_only",
        env["HEAD_SHA"],
        "16 pin value(s) in 11 file(s)",
    ):
        assert expected in result.stdout


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        pytest.param(
            {EXTRA: BASE_FILES[EXTRA].replace("echo hello", "echo bye")},
            f"{EXTRA} line",
            id="non-pin-line-in-another-workflow",
        ),
        pytest.param(
            {W1: SWAP_FILES[W1].replace("echo hello", "echo bye")},
            f"{W1} line",
            id="non-pin-line-in-same-workflow",
        ),
        pytest.param(
            {W1: SWAP_FILES[W1] + "      - run: echo extra\n"},
            "adds or removes a line",
            id="added-step",
        ),
        pytest.param(
            {W1: SWAP_FILES[W1].replace("      - run: echo hello\n", "")},
            "adds or removes a line",
            id="removed-step",
        ),
        pytest.param(
            {".github/workflows/new.yml": _workflow(NEW)},
            "file is added or deleted",
            id="added-workflow",
        ),
        pytest.param(
            {CONTRACT: None}, "file is added or deleted", id="deleted-pin-file"
        ),
        pytest.param(
            {W1: SWAP_FILES[W1].replace("# .github/sibling-pins.yaml", "# changed")},
            f"{W1} line 7",
            id="changed-ref-comment",
        ),
        pytest.param(
            {
                CONTRACT: SWAP_FILES[CONTRACT].replace(
                    "omnimarket_contract_ref:", "renamed:"
                )
            },
            f"{CONTRACT} line 2",
            id="renamed-pin-key",
        ),
        pytest.param({W1: _workflow("main")}, f"{W1} line 7", id="sha-to-branch"),
        pytest.param(
            {W1: _workflow("0.47.39")}, f"{W1} line 7", id="workflow-sha-to-version"
        ),
        pytest.param({"src/x.py": "x = 1\n"}, "src/x.py", id="source-file"),
        pytest.param(
            {"pyproject.toml": PROJECT.replace('name = "x"', 'name = "y"')},
            "project changes outside project.version",
            id="manifest-non-version-change",
        ),
        pytest.param(
            {W1: SWAP_FILES[W1].replace("          ref:", "         ref:")},
            f"{W1} line 7",
            id="changed-indent",
        ),
        pytest.param({W1: _workflow(f'"{NEW}"')}, f"{W1} line 7", id="quoted-sha"),
        pytest.param({W1: _workflow(NEW.upper())}, f"{W1} line 7", id="uppercase-sha"),
        pytest.param(
            {W1: SWAP_FILES[W1].replace("\n", "\r\n")},
            f"{W1} line",
            id="changed-line-endings",
        ),
        pytest.param(
            {"other/pins.yaml": f"pin: {NEW}\n"},
            "other/pins.yaml",
            id="undeclared-pin-file",
        ),
    ],
)
def test_mixed_pin_swap_fails_closed(
    tmp_path: Path, changes: dict[str, str | None], reason: str
) -> None:
    env = _prepare(tmp_path, {**SWAP_FILES, **changes})
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


@pytest.mark.parametrize(
    "manifest", ["pyproject.toml", "nested/pyproject.toml", "uv.lock"]
)
def test_pin_swap_with_dependency_manifests(tmp_path: Path, manifest: str) -> None:
    head = (
        PROJECT.replace("0.1.0", "0.1.1")
        if manifest.endswith("toml")
        else "version = 2\n"
    )
    base = PROJECT if manifest.endswith("toml") else "version = 1\n"
    env = _prepare(
        tmp_path,
        {**SWAP_FILES, manifest: head},
        base_changes={manifest: base},
    )
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "pin-swap-only change" in result.stdout
    assert (
        "manifests: version/dependency-pin keys only: project.version" in result.stdout
    )


@pytest.mark.parametrize("changed_action", [False, True])
def test_workflow_uses_pin_swap(tmp_path: Path, changed_action: bool) -> None:
    base = f"      - uses: actions/checkout@{OLD} # checkout\n"
    head = f"      - uses: actions/checkout@{NEW} # checkout\n"
    if changed_action:
        head = head.replace("actions/checkout", "actions/cache")
    env = _prepare(tmp_path, {W1: head}, base_changes={W1: base})
    result = _run(env)
    _assert_output(env, exempt=not changed_action)
    if changed_action:
        assert "OCC writer app is not exempt:" in result.stdout
        assert f"{W1} line 1" in result.stdout
    else:
        assert "pin-swap-only change" in result.stdout
        assert "1 pin value(s) in 1 file(s)" in result.stdout


@pytest.mark.parametrize("new_value", ["0.47.39", "v0.47.39", NEW])
def test_pin_file_version_swap(tmp_path: Path, new_value: str) -> None:
    base = "pins:\n  omnibase_core: 0.47.35\n"
    head = f"pins:\n  omnibase_core: {new_value}\n"
    env = _prepare(tmp_path, {SIBLINGS: head}, base_changes={SIBLINGS: base})
    result = _run(env)
    _assert_output(env, exempt=new_value != NEW)
    if new_value == NEW:
        assert "OCC writer app is not exempt:" in result.stdout
        assert f"{SIBLINGS} line 2" in result.stdout
    else:
        assert "pin-swap-only change" in result.stdout
        assert "1 pin value(s) in 1 file(s)" in result.stdout


def test_multiple_dependency_manifests_still_refused(tmp_path: Path) -> None:
    head = PROJECT.replace("0.1.0", "0.1.1")
    env = _prepare(
        tmp_path,
        {**SWAP_FILES, "pyproject.toml": head, "nested/pyproject.toml": head},
        base_changes={"nested/pyproject.toml": PROJECT},
    )
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "more than one dependency manifest changed" in result.stdout


def test_writer_pin_swap_step_stays_writer_app_only() -> None:
    assert (
        "steps.bot_exempt.outputs.writer_app == 'true'"
        in _step("writer_pin_only")["if"]
    )


def test_pin_verdict_hook_runs_both_modules_in_the_precommit_suite() -> None:
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / ".pre-commit-config.yaml").read_text())
    hooks = [
        hook
        for repo in config["repos"]
        if repo["repo"] == "local"
        for hook in repo["hooks"]
        if hook["id"] == "receipt-gate-writer-pin-only"
    ]
    assert len(hooks) == 1, "the pin verdict tests need one local pre-commit hook"
    hook = hooks[0]
    command = shlex.split(hook["entry"])
    assert command[:4] == ["uv", "run", "--frozen", "pytest"]
    modules = {
        "tests/ci/test_receipt_gate_writer_pin_only_in_job_omn17427.py",
        "tests/ci/test_receipt_gate_writer_pin_swap_omn20068.py",
    }
    assert {argument for argument in command if argument.endswith(".py")} == modules
    assert not {"-k", "-m", "--collect-only"}.intersection(command)
    assert hook["language"] == "system"
    assert hook["pass_filenames"] is False
    assert "pre-commit" in hook.get("stages", ["pre-commit"])
    for path in modules | {
        ".github/workflows/receipt-gate.yml",
        ".pre-commit-config.yaml",
    }:
        assert re.search(hook["files"], path), f"hook does not run when {path} changes"
        assert not re.search(hook.get("exclude", r"^$"), path)
    skipped = yaml.safe_load((root / ".github/precommit-suite-skip.yaml").read_text())
    assert hook["id"] not in skipped


def test_pin_verdict_step_runs_in_the_precommit_suite_job() -> None:
    """ci.yml names the pin verdict tests in a step of a job CI Summary sweeps.

    The hook above already runs through the Pre-commit Suite, but no workflow
    file named the test module, so nothing that reads ci.yml could see the gate.
    """
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["precommit-suite"]
    assert "if" not in job and "needs" not in job
    assert job.get("continue-on-error") is not True
    marker = "tests/ci/test_receipt_gate_writer_pin_only_in_job_omn17427.py"
    steps = [step for step in job["steps"] if marker in str(step.get("run", ""))]
    assert len(steps) == 1, "the pre-commit suite job needs one step for the pin tests"
    step = steps[0]
    assert step.get("name"), "the pin verdict step must be named"
    assert "if" not in step
    assert step.get("continue-on-error") is not True
    command = shlex.split(str(step["run"]))
    assert command[:4] == ["uv", "run", "--frozen", "pytest"]
    assert {argument for argument in command if argument.endswith(".py")} == {
        marker,
        "tests/ci/test_receipt_gate_writer_pin_swap_omn20068.py",
    }
    assert not {"-k", "-m", "--collect-only"}.intersection(command)
