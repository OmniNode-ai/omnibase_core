# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the onex init project scaffolding command."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.cli.cli_init import _to_package_name


@pytest.mark.unit
class TestOnexInit:
    """Tests for the `onex init` command."""

    def test_onex_init_creates_project(self, tmp_path: object) -> None:
        """Verify that all expected files and directories are created."""
        from pathlib import Path

        base = Path(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "my-project", "--path", str(base)])

        assert result.exit_code == 0, result.output

        project_dir = base / "my-project"
        assert (project_dir / "pyproject.toml").is_file()
        assert (project_dir / "src" / "my_project" / "__init__.py").is_file()
        assert (project_dir / "src" / "my_project" / "nodes" / "__init__.py").is_file()
        assert (project_dir / "tests" / "__init__.py").is_file()
        assert (project_dir / "contracts" / ".gitkeep").is_file()

    def test_onex_init_generated_pyproject_valid(self, tmp_path: object) -> None:
        """Check pyproject.toml content includes omnibase-core and onex.nodes."""
        from pathlib import Path

        base = Path(str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "test-pkg", "--path", str(base)])

        assert result.exit_code == 0, result.output

        content = (base / "test-pkg" / "pyproject.toml").read_text()
        assert "omnibase-core" in content
        assert "onex.nodes" in content
        assert 'name = "test-pkg"' in content
        assert 'packages = ["src/test_pkg"]' in content

    def test_onex_init_rejects_existing_dir(self, tmp_path: object) -> None:
        """Non-empty existing directory should cause non-zero exit."""
        from pathlib import Path

        base = Path(str(tmp_path))
        # Create a non-empty directory
        existing = base / "existing-project"
        existing.mkdir()
        (existing / "some_file.txt").write_text("content")

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "existing-project", "--path", str(base)])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_onex_init_converts_hyphens_to_underscores(self) -> None:
        """Hyphens in project name should become underscores in package name."""
        assert _to_package_name("my-cool-project") == "my_cool_project"
        assert _to_package_name("simple") == "simple"
        assert _to_package_name("has.dots.too") == "has_dots_too"
        assert _to_package_name("MixedCase-Name") == "mixedcase_name"

    def test_onex_init_empty_existing_dir_succeeds(self, tmp_path: object) -> None:
        """An empty existing directory should be reused without error."""
        from pathlib import Path

        base = Path(str(tmp_path))
        empty_dir = base / "empty-project"
        empty_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["init", "empty-project", "--path", str(base)])

        assert result.exit_code == 0, result.output
        assert (empty_dir / "pyproject.toml").is_file()
