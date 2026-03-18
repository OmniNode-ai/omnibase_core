# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for onex new node scaffolding command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


def _create_project(root: Path, name: str = "my_project") -> Path:
    """Create a minimal ONEX project structure for testing.

    Args:
        root: Parent directory to create the project in.
        name: Project directory name (also used as package name).

    Returns:
        Path to the project root.
    """
    project = root / name
    project.mkdir(parents=True)
    # pyproject.toml with onex.nodes entry point (needed for project detection)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "test"\n\n[project.entry-points."onex.nodes"]\n'
    )
    # src/<package>/__init__.py
    pkg_dir = project / "src" / name / "nodes"
    pkg_dir.mkdir(parents=True)
    (project / "src" / name / "__init__.py").write_text("")
    return project


@pytest.mark.unit
def test_onex_new_node_creates_structure(tmp_path: Path) -> None:
    """Verify that 'onex new node' creates all expected files and directories."""
    project = _create_project(tmp_path, "my_project")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "new",
            "node",
            "my-crawler",
            "--type",
            "effect",
            "--project-root",
            str(project),
        ],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    node_dir = project / "src" / "my_project" / "nodes" / "my_crawler"
    assert (node_dir / "contract.yaml").exists()
    assert (node_dir / "node_my_crawler_effect.py").exists()
    assert (node_dir / "handlers" / "handler_my_crawler.py").exists()
    assert (node_dir / "models" / "models_my_crawler.py").exists()
    assert (node_dir / "__init__.py").exists()
    assert (node_dir / "handlers" / "__init__.py").exists()
    assert (node_dir / "models" / "__init__.py").exists()


@pytest.mark.unit
def test_onex_new_node_all_four_types(tmp_path: Path) -> None:
    """Verify that all four node types can be scaffolded."""
    project = _create_project(tmp_path, "proj")
    runner = CliRunner()

    for node_type in ["compute", "effect", "reducer", "orchestrator"]:
        result = runner.invoke(
            cli,
            [
                "new",
                "node",
                f"test-{node_type}",
                "--type",
                node_type,
                "--project-root",
                str(project),
            ],
        )
        assert result.exit_code == 0, f"Failed for {node_type}: {result.output}"
        node_dir = project / "src" / "proj" / "nodes" / f"test_{node_type}"
        assert (node_dir / f"node_test_{node_type}_{node_type}.py").exists()


@pytest.mark.unit
def test_onex_new_node_fails_outside_project(tmp_path: Path) -> None:
    """Verify that 'onex new node' fails when project root has no package."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["new", "node", "hello", "--project-root", str(tmp_path)]
    )
    assert result.exit_code != 0


@pytest.mark.unit
def test_onex_new_node_fails_duplicate(tmp_path: Path) -> None:
    """Verify that creating the same node twice fails."""
    project = _create_project(tmp_path, "dup_test")
    runner = CliRunner()

    result1 = runner.invoke(
        cli,
        ["new", "node", "my-node", "--project-root", str(project)],
    )
    assert result1.exit_code == 0

    result2 = runner.invoke(
        cli,
        ["new", "node", "my-node", "--project-root", str(project)],
    )
    assert result2.exit_code != 0
    assert "already exists" in result2.output


@pytest.mark.unit
def test_onex_new_node_contract_content(tmp_path: Path) -> None:
    """Verify that generated contract.yaml has correct content."""
    project = _create_project(tmp_path, "pkg")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "new",
            "node",
            "data-parser",
            "--type",
            "compute",
            "--project-root",
            str(project),
        ],
    )
    assert result.exit_code == 0

    contract = (
        project / "src" / "pkg" / "nodes" / "data_parser" / "contract.yaml"
    ).read_text()
    assert "name: data_parser" in contract
    assert "node_type: COMPUTE" in contract
    assert "pkg.nodes.data_parser.models.models_data_parser.DataParserInput" in contract
    assert (
        "pkg.nodes.data_parser.models.models_data_parser.DataParserOutput" in contract
    )
    assert "pkg.nodes.data_parser.handlers.handler_data_parser" in contract


@pytest.mark.unit
def test_onex_new_node_default_type_is_compute(tmp_path: Path) -> None:
    """Verify that default node type is compute when --type is omitted."""
    project = _create_project(tmp_path, "defaults")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["new", "node", "my-node", "--project-root", str(project)],
    )
    assert result.exit_code == 0
    node_dir = project / "src" / "defaults" / "nodes" / "my_node"
    assert (node_dir / "node_my_node_compute.py").exists()
