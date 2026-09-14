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
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "propagate-config.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "propagate-config.yml"


def _write_targets(tmp_path: Path, body: str) -> Path:
    targets = tmp_path / "propagation-targets.yaml"
    targets.write_text(textwrap.dedent(body).lstrip())
    return targets


def _write_hook_source(tmp_path: Path) -> Path:
    source = tmp_path / ".pre-commit-hooks.yaml"
    source.write_text(
        textwrap.dedent(
            """
            - id: normalization-symmetry
              name: Validate normalization symmetry
              entry: python -m omnibase_core.validators.normalization_symmetry
              language: python
            - id: validate-gitignore-baseline
              name: Validate canonical gitignore baseline
              description: Copied from the declared source, not synthesized.
              entry: python -m omnibase_core.validators.gitignore_baseline
              language: python
              pass_filenames: false
              stages: [pre-commit]
            """
        ).lstrip()
    )
    return source


def _write_fake_gh(tmp_path: Path, branches: dict[str, str]) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    cases = "\n".join(
        f'  "repos/{repo}") printf \'%s\\n\' "{branch}" ;;'
        for repo, branch in branches.items()
    )
    gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "[[ ${1:-} == api ]] || exit 91\n"
        "case ${2:-} in\n"
        f"{cases}\n"
        "  *) exit 92 ;;\n"
        "esac\n"
    )
    gh.chmod(0o755)
    return bin_dir


def _run(
    targets: Path,
    *,
    propagation_name: str = "normalization-symmetry-hook",
    branches: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PROPAGATION_TARGETS_FILE"] = str(targets)
    env["PROPAGATION_NAME"] = propagation_name
    env["PROPAGATION_DRY_RUN"] = "1"
    env["GITHUB_TOKEN"] = "dry-run-token"
    bin_dir = _write_fake_gh(
        targets.parent,
        branches
        if branches is not None
        else {
            "OmniNode-ai/omnibase_infra": "dev",
            "OmniNode-ai/omnibase_spi": "dev",
            "OmniNode-ai/omniclaude": "dev",
        },
    )
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.unit
def test_dry_run_uses_cross_repo_read_token() -> None:
    """The repository token cannot resolve private sibling default branches."""
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["dry-run-ci-check"]["steps"]
    mint = next(step for step in steps if step.get("id") == "app-token")
    execute = next(step for step in steps if step.get("name") == "Execute dry-run")

    assert mint["with"]["permission-contents"] == "read"
    assert execute["env"]["GITHUB_TOKEN"] == "${{ steps.app-token.outputs.token }}"


@pytest.mark.unit
def test_pr_title_includes_ticket_ref(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
            auto_merge: false
            merge_method: queue_default
        """,
    )
    result = _run(targets)
    assert result.returncode == 0, result.stderr
    create_lines = [
        line for line in result.stdout.splitlines() if "gh pr create" in line
    ]
    assert len(create_lines) == 1
    assert "OMN-9344" in create_lines[0], (
        f"PR title missing OMN-9344 ticket ref: {create_lines[0]}"
    )


@pytest.mark.unit
def test_dry_run_emits_dedup_check(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
            auto_merge: false
            merge_method: queue_default
        """,
    )
    result = _run(targets)
    assert result.returncode == 0, result.stderr
    assert "dedup check" in result.stdout, (
        f"Expected dedup check in dry-run output: {result.stdout}"
    )


@pytest.mark.unit
def test_dry_run_emits_one_pr_per_target(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
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
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
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
    # Per OMN-8838: auto-merge is armed via GraphQL enablePullRequestAutoMerge,
    # never `gh pr merge --auto` (which silently picks the wrong method).
    assert "enablePullRequestAutoMerge" in result.stdout, result.stdout
    assert "SQUASH" in result.stdout


@pytest.mark.unit
def test_unknown_propagation_name_exits_nonzero(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: some-other-hook
            source: {source}
            tracking_issue: OMN-9344
            targets: []
            auto_merge: true
            merge_method: queue_default
        """,
    )
    result = _run(targets, propagation_name="normalization-symmetry-hook")
    assert result.returncode != 0


@pytest.mark.unit
def test_unsupported_merge_method_rejected(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: normalization-symmetry
            auto_merge: true
            merge_method: invalid_method
        """,
    )
    result = _run(targets)
    assert result.returncode != 0
    assert "unsupported merge_method" in (result.stderr + result.stdout).lower()


@pytest.mark.unit
def test_unsupported_operation_rejected(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: normalization-symmetry-hook
            source: {source}
            tracking_issue: OMN-9344
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


@pytest.mark.unit
def test_uses_each_targets_live_default_branch(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: gitignore-baseline-hook
            source: {source}
            tracking_issue: OMN-18033
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: validate-gitignore-baseline
              - repo: OmniNode-ai/omnibase
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: validate-gitignore-baseline
            auto_merge: false
            merge_method: queue_default
        """,
    )
    result = _run(
        targets,
        propagation_name="gitignore-baseline-hook",
        branches={
            "OmniNode-ai/omnibase_infra": "dev",
            "OmniNode-ai/omnibase": "main",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "--repo OmniNode-ai/omnibase_infra --head" in result.stdout
    assert "--base dev" in result.stdout
    assert "--repo OmniNode-ai/omnibase --head" in result.stdout
    assert "--base main" in result.stdout


@pytest.mark.unit
def test_default_branch_lookup_failure_fails_closed(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: gitignore-baseline-hook
            source: {source}
            tracking_issue: OMN-18033
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: validate-gitignore-baseline
            auto_merge: false
            merge_method: queue_default
        """,
    )
    result = _run(
        targets,
        propagation_name="gitignore-baseline-hook",
        branches={},
    )
    assert result.returncode != 0
    assert "default branch" in result.stderr.lower()


@pytest.mark.unit
def test_renders_exact_declared_hook_and_tracking_issue(tmp_path: Path) -> None:
    source = _write_hook_source(tmp_path)
    targets = _write_targets(
        tmp_path,
        f"""
        propagations:
          - name: gitignore-baseline-hook
            source: {source}
            tracking_issue: OMN-18033
            targets:
              - repo: OmniNode-ai/omnibase_infra
                path: .pre-commit-config.yaml
                operation: append_hook_entry
                hook_id: validate-gitignore-baseline
            auto_merge: false
            merge_method: queue_default
        """,
    )
    result = _run(targets, propagation_name="gitignore-baseline-hook")
    assert result.returncode == 0, result.stderr
    assert "OMN-18033" in result.stdout
    assert "OMN-9344" not in result.stdout
    assert (
        "entry: python -m omnibase_core.validators.gitignore_baseline" in result.stdout
    )
    assert (
        "description: Copied from the declared source, not synthesized."
        in result.stdout
    )
    assert "language: python" in result.stdout
    assert "always_run:" not in result.stdout
    assert "stages:" in result.stdout
    assert "- pre-commit" in result.stdout


@pytest.mark.unit
def test_all_declared_hook_ids_exist_in_their_source_manifest() -> None:
    targets = yaml.safe_load(
        (REPO_ROOT / ".github" / "propagation-targets.yaml").read_text()
    )
    for propagation in targets["propagations"]:
        source_hooks = yaml.safe_load((REPO_ROOT / propagation["source"]).read_text())
        source_ids = {hook["id"] for hook in source_hooks}
        for target in propagation["targets"]:
            assert target["hook_id"] in source_ids, (
                f"{propagation['name']} references missing hook "
                f"{target['hook_id']} in {propagation['source']}"
            )
