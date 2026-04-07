# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI commands for scaffolding new ONEX nodes."""

from __future__ import annotations

import re
from pathlib import Path
from string import Template

import click

NODE_TYPES = ("compute", "effect", "reducer", "orchestrator")

CONTRACT_TEMPLATE = Template(
    """\
name: ${node_name}
node_type: ${node_type_upper}
contract_version: "1.0.0"
node_version: "0.1.0"
input_model: ${package}.nodes.${node_name}.models.models_${node_name}.${input_class}
output_model: ${package}.nodes.${node_name}.models.models_${node_name}.${output_class}
handler_routing:
  default: ${package}.nodes.${node_name}.handlers.handler_${node_name}
golden_path: []
dod_evidence: []
"""
)

NODE_PY_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"${node_class} node — ${node_type} type.\"\"\"
from __future__ import annotations


class ${node_class}:
    \"\"\"${node_type_title} node for ${node_name_display}.

    TODO(OMN-XXXX): Implement node logic.
    \"\"\"

    def process(self, input_data: object) -> object:
        \"\"\"Process input and return output.

        TODO(OMN-XXXX): Implement ${node_type} logic for ${node_name_display}.
        \"\"\"
        raise NotImplementedError("${node_class}.process not yet implemented")
"""
)

HANDLER_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"Handler for ${node_name_display}.\"\"\"
from __future__ import annotations


async def handle(input_data: object) -> object:
    \"\"\"Handle ${node_name_display} logic.

    TODO(OMN-XXXX): Implement handler logic for ${node_name_display}.
    \"\"\"
    raise NotImplementedError("handle() for ${node_name_display} not yet implemented")
"""
)

MODELS_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"Models for ${node_name_display}.\"\"\"
from __future__ import annotations

from pydantic import BaseModel


class ${input_class}(BaseModel):
    \"\"\"Input model for ${node_name_display}.\"\"\"


class ${output_class}(BaseModel):
    \"\"\"Output model for ${node_name_display}.\"\"\"
"""
)


def _to_snake(name: str) -> str:
    """Convert a name to snake_case.

    Args:
        name: The name to convert (may contain hyphens, spaces, etc.).

    Returns:
        A valid Python snake_case identifier.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", name.replace("-", "_")).lower()


def _to_class(name: str) -> str:
    """Convert a name to PascalCase.

    Args:
        name: The name to convert (may contain hyphens or underscores).

    Returns:
        A PascalCase class name.
    """
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def _find_project_root(start: Path) -> Path | None:
    """Search upward for pyproject.toml with onex.nodes entry point.

    Args:
        start: Directory to start searching from.

    Returns:
        The project root directory, or None if not found.
    """
    current = start.resolve()
    for _ in range(20):
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if "onex.nodes" in content:
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _detect_package_name(project_root: Path) -> str | None:
    """Detect package name from src/ directory.

    Args:
        project_root: The project root containing src/.

    Returns:
        The package name, or None if no package found.
    """
    src = project_root / "src"
    if not src.exists():
        return None
    for child in sorted(src.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            return child.name
    return None


@click.group("new")
def new_group() -> None:  # stub-ok
    """Scaffold new ONEX components."""


@new_group.command("node")
@click.argument("node_name")
@click.option(
    "--type",
    "node_type",
    type=click.Choice(NODE_TYPES),
    default="compute",
    help="Node type.",
)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Project root (auto-detected if not specified).",
)
def new_node(node_name: str, node_type: str, project_root: Path | None) -> None:
    """Create a new ONEX node with contract, handler, and models.

    NODE_NAME is the name for the new node (e.g., 'my-crawler').
    """
    if project_root is None:
        project_root = _find_project_root(Path.cwd())
        if project_root is None:
            raise click.ClickException(
                "Not inside an ONEX project. Run 'onex init' first, or use --project-root."
            )

    package = _detect_package_name(project_root)
    if package is None:
        raise click.ClickException(f"No Python package found in {project_root / 'src'}")

    snake = _to_snake(node_name)
    cls = _to_class(node_name)
    input_class = f"{cls}Input"
    output_class = f"{cls}Output"

    node_dir = project_root / "src" / package / "nodes" / snake
    if node_dir.exists():
        raise click.ClickException(f"Node directory already exists: {node_dir}")

    node_dir.mkdir(parents=True)
    (node_dir / "__init__.py").write_text("")

    ctx = {
        "node_name": snake,
        "node_type": node_type,
        "node_type_upper": node_type.upper(),
        "node_type_title": node_type.title(),
        "node_class": f"Node{cls}",
        "node_name_display": node_name,
        "package": package,
        "input_class": input_class,
        "output_class": output_class,
    }

    # contract.yaml
    (node_dir / "contract.yaml").write_text(CONTRACT_TEMPLATE.substitute(ctx))

    # node file
    (node_dir / f"node_{snake}_{node_type}.py").write_text(
        NODE_PY_TEMPLATE.substitute(ctx)
    )

    # handlers/
    handlers_dir = node_dir / "handlers"
    handlers_dir.mkdir()
    (handlers_dir / "__init__.py").write_text("")
    (handlers_dir / f"handler_{snake}.py").write_text(HANDLER_TEMPLATE.substitute(ctx))

    # models/
    models_dir = node_dir / "models"
    models_dir.mkdir()
    (models_dir / "__init__.py").write_text("")
    (models_dir / f"models_{snake}.py").write_text(MODELS_TEMPLATE.substitute(ctx))

    click.echo(f"Created {node_type} node '{node_name}' at {node_dir}")
    click.echo("  contract.yaml")
    click.echo(f"  node_{snake}_{node_type}.py")
    click.echo(f"  handlers/handler_{snake}.py")
    click.echo(f"  models/models_{snake}.py")
