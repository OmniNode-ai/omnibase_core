# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for validate_no_new_env_vars.py (OMN-11186)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_VALIDATOR_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "validation"
    / "validate_no_new_env_vars.py"
)

_spec = importlib.util.spec_from_file_location(
    "validate_no_new_env_vars", _VALIDATOR_PATH
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_file = _mod.check_file


def _write_py(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


@pytest.mark.unit
class TestCheckFile:
    def test_new_environ_key_is_flagged(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", 'import os\nx = os.environ["NEW_VAR"]\n')
        violations = check_file(p)
        assert len(violations) == 1
        assert violations[0][2] == "NEW_VAR"

    def test_new_getenv_is_flagged(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", 'import os\nx = os.getenv("NEW_VAR")\n')
        violations = check_file(p)
        assert len(violations) == 1
        assert violations[0][2] == "NEW_VAR"

    def test_new_environ_get_is_flagged(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", 'import os\nx = os.environ.get("NEW_VAR")\n')
        violations = check_file(p)
        assert len(violations) == 1
        assert violations[0][2] == "NEW_VAR"

    def test_allowlisted_omni_home_is_clean(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", 'import os\nx = os.environ["OMNI_HOME"]\n')
        assert check_file(p) == []

    def test_allowlisted_ci_is_clean(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", 'import os\nx = os.environ.get("CI")\n')
        assert check_file(p) == []

    def test_allowlisted_kafka_is_clean(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path, "foo.py", 'import os\nx = os.environ["KAFKA_BOOTSTRAP_SERVERS"]\n'
        )
        assert check_file(p) == []

    def test_env_var_ok_annotation_suppresses(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            "foo.py",
            'import os\nx = os.environ["NEW_VAR"]  # env-var-ok\n',
        )
        assert check_file(p) == []

    def test_test_file_is_skipped(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        p = _write_py(
            tests_dir, "test_foo.py", 'import os\nx = os.environ["NEW_VAR"]\n'
        )
        assert check_file(p) == []

    def test_scripts_file_is_skipped(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        p = _write_py(
            scripts_dir,
            "validate_something.py",
            'import os\nx = os.environ["NEW_VAR"]\n',
        )
        assert check_file(p) == []

    def test_examples_file_is_skipped(self, tmp_path: Path) -> None:
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        p = _write_py(
            examples_dir, "demo.py", 'import os\nx = os.getenv("ANTHROPIC_API_KEY")\n'
        )
        assert check_file(p) == []

    def test_clean_file_returns_empty(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", "x = 1\n")
        assert check_file(p) == []

    def test_comment_line_is_skipped(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "foo.py", '# os.environ["NEW_VAR"]\n')
        assert check_file(p) == []

    def test_multiple_violations_reported(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path,
            "foo.py",
            'import os\na = os.environ["A_VAR"]\nb = os.getenv("B_VAR")\n',
        )
        violations = check_file(p)
        assert len(violations) == 2

    def test_non_python_file_ignored(self, tmp_path: Path) -> None:
        p = tmp_path / "config.yaml"
        p.write_text('env: os.environ["NEW_VAR"]\n', encoding="utf-8")
        assert check_file(p) == []


@pytest.mark.unit
class TestMainExitCodes:
    def _run(self, *args: str) -> int:
        result = subprocess.run(
            [sys.executable, str(_VALIDATOR_PATH), *args],
            capture_output=True,
            check=False,
        )
        return result.returncode

    def test_exit_0_when_no_violations(self, tmp_path: Path) -> None:
        p = _write_py(tmp_path, "clean.py", "x = 1\n")
        assert self._run(str(p)) == 0

    def test_exit_1_when_violations(self, tmp_path: Path) -> None:
        p = _write_py(
            tmp_path, "bad.py", 'import os\nx = os.environ["BRAND_NEW_VAR"]\n'
        )
        assert self._run(str(p)) == 1

    def test_exit_0_with_no_files(self) -> None:
        assert self._run() == 0
