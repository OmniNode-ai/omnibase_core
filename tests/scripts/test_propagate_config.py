# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for scripts/propagate-config.sh.

OMN-9344: cross-repo config propagator bot. The script is invoked by
.github/workflows/propagate-config.yml on release-tag events and opens a PR
in every downstream target declared in .github/propagation-targets.yaml.

These tests drive the script in --dry-run mode so that gh invocations are
printed to stdout rather than executed. Dry-run output is the contract the
workflow depends on, so assertions here double as the behavioral spec.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "propagate-config.sh"


def _write_targets(tmp_path: Path, body: str) -> Path:
    targets = tmp_path / "propagation-targets.yaml"
    targets.write_text(textwrap.dedent(body).lstrip())
    return targets


def _run(
    targets: Path, *, propagation_name: str = "normalization-symmetry-hook"
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PROPAGATION_TARGETS_FILE"] = str(targets)
    env["PROPAGATION_NAME"] = propagation_name
    env["PROPAGATION_DRY_RUN"] = "1"
    env["GITHUB_TOKEN"] = "dry-run-token"
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.unit
def test_dry_run_emits_one_pr_per_target(tmp_path: Path) -> None:
    targets = _write_targets(
        tmp_path,
        """
        propagations:
          - name: normalization-symmetry-hook
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
              - repo: OmniNode-ai/omnibase_spi
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
              - repo: OmniNode-ai/omniclaude
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
            auto_merge: true
            merge_method: queue_default
        """,
    )
    result = _run(targets)
    assert result.returncode == 0, result.stderr
    create_invocations = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("DRY_RUN: gh pr create")
    ]
    assert len(create_invocations) == 3, result.stdout
    for repo in ("omnibase_infra", "omnibase_spi", "omniclaude"):
        assert any(f"OmniNode-ai/{repo}" in line for line in create_invocations), repo


@pytest.mark.unit
def test_dry_run_arms_auto_merge_per_pr(tmp_path: Path) -> None:
    targets = _write_targets(
        tmp_path,
        """
        propagations:
          - name: normalization-symmetry-hook
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
            auto_merge: true
            merge_method: queue_default
        """,
    )
    result = _run(targets)
    assert result.returncode == 0, result.stderr
    assert "DRY_RUN: gh pr merge" in result.stdout, result.stdout
    assert "--auto" in result.stdout


@pytest.mark.unit
def test_unknown_propagation_name_exits_nonzero(tmp_path: Path) -> None:
    targets = _write_targets(
        tmp_path,
        """
        propagations:
          - name: some-other-hook
            targets: []
            auto_merge: true
            merge_method: queue_default
        """,
    )
    result = _run(targets, propagation_name="normalization-symmetry-hook")
    assert result.returncode != 0


@pytest.mark.unit
def test_unsupported_operation_rejected(tmp_path: Path) -> None:
    targets = _write_targets(
        tmp_path,
        """
        propagations:
          - name: normalization-symmetry-hook
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: overwrite_file
                hook_id: normalization-symmetry
            auto_merge: true
            merge_method: queue_default
        """,
    )
    result = _run(targets)
    assert result.returncode != 0
    assert "unsupported operation" in (result.stderr + result.stdout).lower()
