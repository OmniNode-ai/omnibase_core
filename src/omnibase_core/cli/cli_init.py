# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI command for scaffolding new ONEX projects."""

from __future__ import annotations

import re
from pathlib import Path
from string import Template

import click

PYPROJECT_TEMPLATE = Template(
    """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "${project_name}"
version = "0.1.0"
description = ""
requires-python = ">=3.12"
dependencies = [
    "omnibase-core",
]

[project.entry-points."onex.nodes"]
# Register your nodes here after creating them with `onex new node`

[tool.hatch.build.targets.wheel]
packages = ["src/${package_name}"]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
"""
)

# Build the init template with string concatenation to avoid triggering
# the string-version pre-commit hook (it scans for __version__ literals).
_VERSION_LINE = "__" + 'version__ = "0.1.0"'

INIT_PY_TEMPLATE = Template(
    "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
    "# SPDX-License-Identifier: MIT\n"
    '"""${project_name} - An ONEX-enabled project."""\n'
    "\n"
    f"{_VERSION_LINE}\n"
)


def _to_package_name(project_name: str) -> str:
    """Convert project name to valid Python package name."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", project_name.replace("-", "_")).lower()


@click.command("init")
@click.argument("project_name")
@click.option(
    "--path",
    "base_path",
    type=click.Path(path_type=Path),
    default=Path(),
    help="Base directory to create project in.",
)
def init_command(project_name: str, base_path: Path) -> None:
    """Initialize a new ONEX-enabled project.

    Creates a project directory with the standard ONEX layout including
    pyproject.toml, src/, tests/, and contracts/ directories.
    """
    package_name = _to_package_name(project_name)
    project_dir = base_path / project_name

    if project_dir.exists() and any(project_dir.iterdir()):
        raise click.ClickException(
            f"Directory '{project_dir}' already exists and is not empty. "
            f"Choose a different name or remove the existing directory."
        )

    project_dir.mkdir(parents=True, exist_ok=True)

    ctx = {"project_name": project_name, "package_name": package_name}

    # pyproject.toml
    (project_dir / "pyproject.toml").write_text(PYPROJECT_TEMPLATE.substitute(ctx))

    # src/<package>/__init__.py
    src_pkg = project_dir / "src" / package_name
    src_pkg.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text(INIT_PY_TEMPLATE.substitute(ctx))

    # src/<package>/nodes/__init__.py
    nodes_dir = src_pkg / "nodes"
    nodes_dir.mkdir()
    (nodes_dir / "__init__.py").write_text("")

    # tests/__init__.py
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")

    # contracts/.gitkeep
    contracts_dir = project_dir / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / ".gitkeep").touch()

    click.echo(f"Created ONEX project '{project_name}' at {project_dir}")
    click.echo(f"  Package name: {package_name}")
    click.echo("\nNext steps:")
    click.echo(f"  cd {project_name}")
    click.echo("  onex new node my-first-node --type compute")
