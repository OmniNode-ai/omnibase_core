# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression coverage for no-project pre-commit parity validators."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_NAMES = (
    "validate_precommit_fail_loud.py",
    "validate_precommit_pin_parity.py",
)


def _standalone_script(tmp_path: Path, script_name: str) -> Path:
    """Copy one validator into an isolated no-project repository layout."""
    target = tmp_path / "scripts" / "validation" / script_name
    target.parent.mkdir(parents=True)
    shutil.copy2(_REPO_ROOT / "scripts" / "validation" / script_name, target)
    return target


def _run_no_project(script: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the validator exactly as its CI job does."""
    return subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--with",
            "pyyaml",
            "--with",
            "pydantic",
            "python3",
            str(script),
        ],
        cwd=script.parents[2],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
@pytest.mark.parametrize("script_name", _SCRIPT_NAMES)
def test_no_project_validator_does_not_import_omnibase_core(
    tmp_path: Path, script_name: str
) -> None:
    """The declared standalone runner succeeds without the project package."""
    script = _standalone_script(tmp_path, script_name)
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")

    result = _run_no_project(script)

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize("script_name", _SCRIPT_NAMES)
@pytest.mark.parametrize(
    ("config_content", "expected_error"),
    [
        ("repos: [\n", "did not validate"),
        ("[]\n", "did not validate"),
        ("repos: []\nunknown: true\n", "did not validate"),
    ],
)
def test_no_project_validator_fails_loudly_for_invalid_yaml_shape(
    tmp_path: Path, script_name: str, config_content: str, expected_error: str
) -> None:
    """Malformed and non-mapping configuration remain standalone-runner errors."""
    script = _standalone_script(tmp_path, script_name)
    (tmp_path / ".pre-commit-config.yaml").write_text(config_content, encoding="utf-8")

    result = _run_no_project(script)

    assert result.returncode == 1
    assert expected_error in result.stderr
