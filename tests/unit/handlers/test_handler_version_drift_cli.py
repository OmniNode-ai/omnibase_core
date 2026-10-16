# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the version-drift CLIs over real git clones in a temp dir (OMN-19998)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.handlers import (
    handler_merge_queue_parity_cli,
    handler_version_floor_consumers_cli,
)

pytestmark = pytest.mark.unit


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(cwd),
        },
    ).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _clone_with_origin(tmp: Path, name: str, files: dict[str, str]) -> Path:
    upstream = tmp / "upstream" / name
    upstream.mkdir(parents=True)
    _git(upstream, "init", "-q", "-b", "dev")
    _commit(upstream, files, "init")
    clone = tmp / "registry" / name
    clone.parent.mkdir(parents=True, exist_ok=True)
    _git(tmp, "clone", "-q", str(upstream), str(clone))
    return clone


def _market(core_spec: str) -> str:
    return (
        '[project]\nname = "omnimarket"\nversion = "1"\n'
        f'dependencies = ["omnibase-core{core_spec}"]\n'
    )


def _infra(exact: str) -> str:
    return (
        '[project]\nname = "omnibase-infra"\ndependencies = ["omnibase-core>=0.47.0"]\n'
        f'[tool.uv]\noverride-dependencies = ["omnibase-core=={exact}"]\n'
    )


@pytest.fixture
def market(tmp_path: Path) -> tuple[Path, str]:
    repo = _clone_with_origin(
        tmp_path, "omnimarket", {"pyproject.toml": _market(">=0.47.39")}
    )
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, {"pyproject.toml": _market(">=0.47.44")}, "raise")
    return repo, base


def test_floor_cli_fails_a_raise_ahead_of_a_cloned_consumer(
    tmp_path: Path, market: tuple[Path, str], capsys: pytest.CaptureFixture[str]
) -> None:
    repo, base = market
    _clone_with_origin(
        tmp_path, "omnibase_infra", {"pyproject.toml": _infra("0.47.39")}
    )
    _clone_with_origin(tmp_path, "omnidash", {"package.json": "{}"})
    code = handler_version_floor_consumers_cli.main(
        [
            "--root",
            str(repo),
            "--repo",
            "omnimarket",
            "--base-ref",
            base,
            "--consumers-root",
            str(tmp_path / "registry"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert (
        "omnibase_infra: omnimarket raises its omnibase-core floor 0.47.39 -> 0.47.44"
        in out
    )
    assert "origin/dev" in out
    assert "omnidash" not in out


def test_floor_cli_passes_when_the_consumer_already_pins_the_floor(
    tmp_path: Path, market: tuple[Path, str]
) -> None:
    repo, base = market
    for name in (
        "omnibase_compat",
        "omnibase_spi",
        "onex_change_control",
        "omnimemory",
        "omniintelligence",
        "omniclaude",
        "omnigemini",
        "omnidash",
        "omniweb",
        "omnibase_internal",
        "omninode_infra",
    ):
        _clone_with_origin(tmp_path, name, {"README": "x"})
    _clone_with_origin(
        tmp_path, "omnibase_infra", {"pyproject.toml": _infra("0.47.44")}
    )
    code = handler_version_floor_consumers_cli.main(
        [
            "--root",
            str(repo),
            "--repo",
            "omnimarket",
            "--base-ref",
            base,
            "--consumers-root",
            str(tmp_path / "registry"),
        ]
    )
    assert code == 0


def test_floor_cli_ignores_staged_files_that_are_not_pyproject(
    market: tuple[Path, str],
) -> None:
    repo, _ = market
    assert (
        handler_version_floor_consumers_cli.main(["--root", str(repo), "src/a.py"]) == 0
    )


def test_floor_cli_refuses_a_missing_base_ref(market: tuple[Path, str]) -> None:
    repo, _ = market
    code = handler_version_floor_consumers_cli.main(
        ["--root", str(repo), "--repo", "omnimarket", "--base-ref", "no-such-ref"]
    )
    assert code == 1


_QUEUE_ONLY = (
    "on:\n  pull_request:\n  merge_group:\njobs:\n  j:\n"
    "    if: github.event_name == 'merge_group'\n    runs-on: x\n    steps: []\n"
)
_BASELINE = (
    "violations:\n  - path: .github/workflows/ci.yml\n    job: j\n"
    "    rule: merge_queue_only_if\n    ticket: OMN-19998\n"
)


def test_parity_cli_fails_then_warns_once_baselined(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _commit(repo, {".github/workflows/ci.yml": _QUEUE_ONLY}, "wf")
    assert handler_merge_queue_parity_cli.main(["--root", str(repo)]) == 1
    _commit(repo, {".onex_ratchets/merge_queue_parity_baseline.yaml": _BASELINE}, "bl")
    assert handler_merge_queue_parity_cli.main(["--root", str(repo)]) == 0


def test_parity_cli_refuses_baseline_growth_against_the_base(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    base = _commit(
        repo,
        {
            ".github/workflows/ci.yml": "on: [push]\njobs: {}\n",
            ".onex_ratchets/merge_queue_parity_baseline.yaml": "violations: []\n",
        },
        "base",
    )
    _commit(
        repo,
        {
            ".github/workflows/ci.yml": _QUEUE_ONLY,
            ".onex_ratchets/merge_queue_parity_baseline.yaml": _BASELINE,
        },
        "grow",
    )
    assert (
        handler_merge_queue_parity_cli.main(
            ["--root", str(repo), "--ratchet-base-ref", base]
        )
        == 1
    )
