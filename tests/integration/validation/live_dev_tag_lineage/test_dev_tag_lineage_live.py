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
_IDENTITY_RULES = ",".join(
    rule.rule_id
    for rule in ValidatorDevTagLineage().contract.rules
    if (rule.parameters or {})["phase"] == "identity"
)


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
    ("tag", "spec", "override", "source_kind", "rules", "exit_code", "rule"),
    [
        (_REAL, ">=0.47.58,<0.48.0", None, "tag", None, 0, None),
        (
            _REAL,
            ">=0.47.58,<0.48.0",
            "==0.47.58",
            "tag",
            None,
            1,
            "first_party_version_override",
        ),
        (_REAL, ">=0.47.58,<0.48.0", "==0.47.58", "tag", _IDENTITY_RULES, 0, None),
        (_MISSING, ">=0.47.58,<0.48.0", None, "tag", None, 1, "tag_absent"),
        (_REAL, ">=0.47.58,<0.48.0", None, "rev", None, 1, "first_party_not_dev_tag"),
        (
            _REAL,
            ">=0.47.58,<0.48.0",
            None,
            "release",
            None,
            1,
            "first_party_release_only",
        ),
        (_REAL, ">=0.48.0,<0.49.0", None, "tag", None, 1, "declared_version_mismatch"),
    ],
)
def test_cli_from_external_directory(
    tmp_path: Path,
    tag: str,
    spec: str,
    override: str | None,
    source_kind: str,
    rules: str | None,
    exit_code: int,
    rule: str | None,
) -> None:
    text = _source(tag, spec, override)
    if source_kind == "rev":
        text = text.replace(f'tag = "{tag}"', f'rev = "{"a" * 40}"')
    elif source_kind == "release":
        text = text[: text.index("[tool.uv.sources]")]
    (tmp_path / "pyproject.toml").write_text(text)
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
            *(["--rules", rules] if rules is not None else []),
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
