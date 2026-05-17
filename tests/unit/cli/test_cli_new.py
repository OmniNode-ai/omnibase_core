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
def test_onex_new_node_contract_has_runtime_profiles(tmp_path: Path) -> None:
    """Verify generated contract.yaml includes runtime_profiles in descriptor block."""
    project = _create_project(tmp_path, "runtime_check")
    runner = CliRunner()

    for node_type, expected_profile in [
        ("compute", "compute"),
        ("effect", "effects"),
        ("reducer", "reducers"),
        ("orchestrator", "effects"),
    ]:
        result = runner.invoke(
            cli,
            [
                "new",
                "node",
                f"node-{node_type}",
                "--type",
                node_type,
                "--project-root",
                str(project),
            ],
        )
        assert result.exit_code == 0, f"Failed for {node_type}: {result.output}"
        contract = (
            project
            / "src"
            / "runtime_check"
            / "nodes"
            / f"node_{node_type}"
            / "contract.yaml"
        ).read_text()
        assert "runtime_profiles:" in contract, f"{node_type} missing runtime_profiles"
        assert f"- {expected_profile}" in contract, (
            f"{node_type} missing profile {expected_profile!r}"
        )
        assert "descriptor:" in contract, f"{node_type} missing descriptor block"


@pytest.mark.unit
def test_onex_new_node_contract_has_event_bus(tmp_path: Path) -> None:
    """Verify generated contract.yaml includes event_bus with subscribe/publish topics."""
    project = _create_project(tmp_path, "event_bus_check")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "new",
            "node",
            "my-processor",
            "--type",
            "effect",
            "--project-root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    contract = (
        project / "src" / "event_bus_check" / "nodes" / "my_processor" / "contract.yaml"
    ).read_text()
    assert "event_bus:" in contract
    assert "subscribe_topics:" in contract
    assert "publish_topics:" in contract
    assert "onex.cmd." in contract
    assert "onex.evt." in contract


@pytest.mark.unit
def test_onex_new_node_handler_has_data_provenance_stub(tmp_path: Path) -> None:
    """Verify scaffolded handler includes data_provenance guidance comment."""
    project = _create_project(tmp_path, "provenance_check")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "new",
            "node",
            "my-reducer",
            "--type",
            "reducer",
            "--project-root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    handler = (
        project
        / "src"
        / "provenance_check"
        / "nodes"
        / "my_reducer"
        / "handlers"
        / "handler_my_reducer.py"
    ).read_text()
    assert "data_provenance" in handler
    assert "EnumDataProvenance" in handler


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


@pytest.mark.unit
def test_onex_new_node_stubs_have_descriptive_errors(tmp_path: Path) -> None:
    """Verify scaffolded stubs have descriptive NotImplementedError messages."""
    project = _create_project(tmp_path, "stub_check")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "new",
            "node",
            "my-widget",
            "--type",
            "effect",
            "--project-root",
            str(project),
        ],
    )
    assert result.exit_code == 0

    node_dir = project / "src" / "stub_check" / "nodes" / "my_widget"

    # Node file should have descriptive NotImplementedError
    node_content = (node_dir / "node_my_widget_effect.py").read_text()
    assert (
        'NotImplementedError("NodeMyWidget.process not yet implemented")'
        in node_content
    )
    assert "TODO(OMN-XXXX)" in node_content

    # Handler should have descriptive NotImplementedError
    handler_content = (node_dir / "handlers" / "handler_my_widget.py").read_text()
    assert "NotImplementedError" in handler_content
    assert "not yet implemented" in handler_content

    # Models should be clean (no NotImplementedError)
    models_content = (node_dir / "models" / "models_my_widget.py").read_text()
    assert "NotImplementedError" not in models_content
    assert "MyWidgetInput" in models_content
    assert "MyWidgetOutput" in models_content
