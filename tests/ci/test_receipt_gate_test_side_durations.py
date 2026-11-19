# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-25969: per-test duration records do not cost a tests-only diff its TEST_ONLY_DIFF waiver.

The OMN-23560 duration check makes every new test file add a record under
config/test_file_durations.d/. The must-fail control step of receipt-gate.yml treats
every path that is neither test-side nor the cited contract as product, so before this
change a tests-only diff with its records lost the waiver and fell back to a merge-base
control that cannot fail when the fix already merged. These cases run the step's own
decision lines, cut from the workflow text, over prepared diffs.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
CONTROL_STEP = "Must-fail control at the merge base"
PREPARE_STEP = "Prepare the merge base with the pull request's test side laid over it"
RECORD = "config/test_file_durations.d/tests__unit__test_new.json"


def _script(name: str) -> str:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    script = next(
        step["run"]
        for step in workflow["jobs"]["dod-verify"]["steps"]
        if step.get("name") == name
    )
    assert isinstance(script, str)
    return script


def _test_only_block() -> str:
    """The control step's lines from its TEST_SIDE pattern to its has_tests rule."""
    lines = _script(CONTROL_STEP).splitlines()
    start = next(i for i, line in enumerate(lines) if "TEST_SIDE=" in line)
    end = next(
        i
        for i in range(start, len(lines))
        if lines[i].strip() == 'if [ "$has_tests" = false ]; then'
    )
    block = [line for line in lines[start : end + 3] if "git -C" not in line]
    return "\n".join(block)


def _test_only(tmp_path: Path, paths: list[str]) -> str:
    dod = tmp_path / "dod"
    dod.mkdir()
    (dod / "tickets.txt").write_text("OMN-1\n")
    (dod / "control-diff-paths.txt").write_bytes(
        b"".join(p.encode() + b"\0" for p in paths)
    )
    program = _test_only_block() + '\nprintf "%s" "$test_only"\n'
    completed = subprocess.run(
        ["bash", "-c", program],
        env={"RUNNER_TEMP": str(tmp_path), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_tests_contract_and_duration_record_keep_the_waiver(tmp_path: Path) -> None:
    paths = ["tests/unit/test_new.py", "contracts/OMN-1.yaml", RECORD]
    assert _test_only(tmp_path, paths) == "true"


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_product_change_with_a_record_still_needs_a_control(tmp_path: Path) -> None:
    paths = ["tests/unit/test_new.py", RECORD, "src/pkg/module.py"]
    assert _test_only(tmp_path, paths) == "false"


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_other_config_change_still_needs_a_control(tmp_path: Path) -> None:
    paths = ["tests/unit/test_new.py", "config/test_file_durations.json"]
    assert _test_only(tmp_path, paths) == "false"


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_a_record_alone_is_not_a_test(tmp_path: Path) -> None:
    assert _test_only(tmp_path, [RECORD, "contracts/OMN-1.yaml"]) == "false"


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_merged_fix_binding_accepts_a_duration_record_as_not_product() -> None:
    """The Binds-Merged-Fix product check reads a record the same way."""
    lines = _script(PREPARE_STEP).splitlines()
    patterns = [
        line.strip()
        for line in lines
        if line.strip().startswith(("TEST_SIDE=", "TEST_RECORDS="))
    ]
    check = next(
        line.strip()
        for line in lines
        if "^contracts/OMN-[0-9]+\\.yaml$ ]]; then" in line and "! " in line
    )
    verdicts = {}
    for path in (RECORD, "src/pkg/module.py"):
        program = "\n".join(
            [
                *patterns,
                f"path='{path}'",
                check,
                "  echo product",
                "else",
                "  echo not-product",
                "fi",
            ]
        )
        completed = subprocess.run(
            ["bash", "-c", program], capture_output=True, text=True, check=False
        )
        assert completed.returncode == 0, completed.stderr
        verdicts[path] = completed.stdout.strip()
    assert verdicts == {RECORD: "not-product", "src/pkg/module.py": "product"}
