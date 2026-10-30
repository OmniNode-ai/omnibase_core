# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Opt-in GitHub proof and CLI invocation from a directory outside omnibase_core."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from omnibase_core.nodes.node_dev_tag_lineage_effect.handler import (
    NodeDevTagLineageEffect,
)
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = [pytest.mark.integration, pytest.mark.timeout(240)]
_URL = "https://github.com/OmniNode-ai/omnibase_core.git"
_REAL = "dev-20261029143607-342000ec5702"
_MISSING = "dev-20261029143607-000000000000"


def _source(
    tag: str, spec: str = ">=0.47.58,<0.48.0", override: str | None = None
) -> str:
    text = f'[project]\nname = "consumer"\nversion = "1.0.0"\ndependencies = ["omnibase-core{spec}"]\n[tool.uv.sources]\nomnibase-core = {{git = "{_URL}", tag = "{tag}"}}\n'

    if override is not None:
        text += f'\n[tool.uv]\noverride-dependencies = ["omnibase-core{override}"]\n'
    return text


@pytest.mark.parametrize(("tag", "expected"), [(_REAL, []), (_MISSING, ["tag_absent"])])
def test_github_tag_identity(tmp_path: Path, tag: str, expected: list[str]) -> None:
    (tmp_path / "pyproject.toml").write_text(_source(tag))
    result = ValidatorDevTagLineage(
        root=tmp_path, resolver=NodeDevTagLineageEffect().handle
    ).validate(tmp_path)
    assert [issue.rule_name for issue in result.issues] == expected


@pytest.mark.parametrize(
    ("tag", "spec", "override", "exit_code", "rule"),
    [
        (_REAL, ">=0.47.58,<0.48.0", None, 0, None),
        (_REAL, ">=0.47.58,<0.48.0", "==0.47.58", 0, None),
        (_MISSING, ">=0.47.58,<0.48.0", None, 1, "tag_absent"),
        (_REAL, ">=0.48.0,<0.49.0", None, 1, "declared_version_mismatch"),
    ],
)
def test_cli_from_external_directory(
    tmp_path: Path,
    tag: str,
    spec: str,
    override: str | None,
    exit_code: int,
    rule: str | None,
) -> None:
    (tmp_path / "pyproject.toml").write_text(_source(tag, spec, override))
    env = scrub_git_location_env()
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "UV_PYTHON",
    ):
        env.pop(key, None)
    worktree = Path(__file__).resolve().parents[4]
    env["PATH"] = os.pathsep.join(
        location
        for location in env["PATH"].split(os.pathsep)
        if location
        and not Path(location).resolve().is_relative_to(worktree)
        and not {".venv", "venv", "builds-v0"}.intersection(Path(location).parts)
    )
    env["UV_CACHE_DIR"] = str(tmp_path / "consumer-cache")
    result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--with",
            f"omnibase-core @ {worktree.as_uri()}",
            "python",
            "-m",
            "omnibase_core.nodes.node_dev_tag_lineage_effect.runtime_dev_tag_lineage",
            "pyproject.toml",
            "--package",
            "omnibase-core",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=230,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    if rule is not None:
        assert rule in result.stdout
