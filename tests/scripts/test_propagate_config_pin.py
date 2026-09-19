# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency pinning in scripts/propagate-config.sh (OMN-18033).

A propagated `language: python` hook gets an empty virtualenv in the target
repo. Without the source package travelling with it the hook dies on every
commit with ModuleNotFoundError, which is why the gitignore-baseline rollout
reached none of its twelve declared targets.

The subprocess environment here is built with monkeypatch rather than a copy
of os.environ: raw process-environment access is a hard gate in this repo
(OMN-17744) and these tests do not need one.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "propagate-config.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "propagate-config.yml"
TARGETS_FILE = REPO_ROOT / ".github" / "propagation-targets.yaml"

_SHA = "1" * 40


def _write_source(tmp_path: Path) -> Path:
    source = tmp_path / ".pre-commit-hooks.yaml"
    source.write_text(
        textwrap.dedent(
            """
            - id: validate-gitignore-baseline
              name: Gitignore Baseline Validator
              entry: python -m omnibase_core.validators.gitignore_baseline
              language: python
              pass_filenames: false
              stages: [pre-commit]
            """
        ).lstrip()
    )
    return source


def _write_targets(tmp_path: Path, *, pin: str | None) -> Path:
    pin_line = f"    pin_source_dependency: {pin}\n" if pin else ""
    targets = tmp_path / "propagation-targets.yaml"
    targets.write_text(
        textwrap.dedent(
            f"""
            propagations:
              - name: gitignore-baseline-hook
                source: {_write_source(tmp_path)}
                tracking_issue: OMN-18033
                targets:
                  - repo: OmniNode-ai/omnibase_infra
                    path: .pre-commit-config.yaml
                    operation: append_hook_entry
                    hook_id: validate-gitignore-baseline
            """
        ).lstrip()
        + pin_line
        + "    auto_merge: false\n    merge_method: queue_default\n"
    )
    return targets


def _write_fake_gh(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "[[ ${1:-} == api ]] || exit 91\n"
        "case ${2:-} in\n  \"repos/OmniNode-ai/omnibase_infra\") printf 'dev\\n' ;;\n"
        "  *) exit 92 ;;\nesac\n"
    )
    gh.chmod(0o755)
    return bin_dir


def _run(
    targets: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_sha: str = _SHA,
) -> subprocess.CompletedProcess[str]:
    monkeypatch.setenv("PROPAGATION_TARGETS_FILE", str(targets))
    monkeypatch.setenv("PROPAGATION_NAME", "gitignore-baseline-hook")
    monkeypatch.setenv("PROPAGATION_DRY_RUN", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "dry-run-token")
    monkeypatch.setenv("PROPAGATION_SOURCE_SHA", source_sha)
    monkeypatch.setenv("PATH", str(_write_fake_gh(targets.parent)), prepend=os.pathsep)
    return subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, check=False
    )


@pytest.mark.unit
def test_declared_pin_reaches_the_rendered_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(_write_targets(tmp_path, pin="omnibase-core"), monkeypatch)
    assert result.returncode == 0, result.stderr
    expected = (
        "omnibase-core @ git+https://github.com/OmniNode-ai/omnibase_core.git@" + _SHA
    )
    assert expected in result.stdout, result.stdout


@pytest.mark.unit
def test_pin_without_a_resolvable_sha_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unpinned dependency installs whatever HEAD happens to be at install time."""
    result = _run(
        _write_targets(tmp_path, pin="omnibase-core"),
        monkeypatch,
        source_sha="not-a-sha",
    )
    assert result.returncode == 10, result.stdout + result.stderr
    assert "refusing to propagate an unpinned hook" in result.stderr


@pytest.mark.unit
def test_propagation_without_a_pin_renders_the_hook_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(_write_targets(tmp_path, pin=None), monkeypatch)
    assert result.returncode == 0, result.stderr
    assert "additional_dependencies" not in result.stdout


@pytest.mark.unit
def test_live_gitignore_propagation_declares_its_pin() -> None:
    """The shipped manifest, not a fixture: the rollout OMN-18033 is about."""
    manifest = yaml.safe_load(TARGETS_FILE.read_text())
    entry = next(
        p for p in manifest["propagations"] if p["name"] == "gitignore-baseline-hook"
    )
    assert entry["pin_source_dependency"] == "omnibase-core"


@pytest.mark.unit
def test_workflow_passes_the_source_sha_to_the_propagator() -> None:
    """Without it the pin falls back to git rev-parse HEAD, or fails closed."""
    workflow = yaml.safe_load(WORKFLOW.read_text())
    run_step = next(
        step
        for step in workflow["jobs"]["propagate"]["steps"]
        if step.get("name") == "Run propagator"
    )
    assert run_step["env"]["PROPAGATION_SOURCE_SHA"] == "${{ github.sha }}"
