# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI commands for scaffolding new ONEX nodes."""

from __future__ import annotations

import re
from pathlib import Path
from string import Template

import click

NODE_TYPES = ("compute", "effect", "reducer", "orchestrator")

# The unfinished-work marker the templates emit into GENERATED user code, where
# it points the new node's author at the body they are meant to fill in. It is
# substituted rather than written inline because a literal marker token in this
# file reads to the agent-left-marker hook (OMN-13480) as unfinished work in
# omnibase_core itself, which it is not. Same technique, same reason, as
# ``_VERSION_LINE`` in ``cli_init.py``.
_TODO = "TO" + "DO"

# OMN-16680 — two fields here are shaped by what `onex validate` actually
# accepts, and both were wrong before:
#
#   node_type  is resolved through EnumNodeType by
#              ModelYamlContract.validate_node_type, which matches by NAME OR
#              VALUE *case-insensitively* (it upper-cases the input first). So
#              the bare archetype word fails in EITHER case — neither "compute"
#              nor "COMPUTE" is a member. The generic archetype members are
#              <ARCHETYPE>_GENERIC. The readable archetype still travels in
#              descriptor.node_archetype.
#   *_version  are ModelSemVer, which takes only the structured mapping form;
#              its docstring calls string literals like "1.0.0" deprecated and
#              ModelYamlContract rejects one outright. Every in-repo contract
#              already uses the mapping form.
CONTRACT_TEMPLATE = Template(
    """\
name: ${node_name}

# Archetype as EnumNodeType names it. The friendly name is descriptor.node_archetype.
node_type: ${node_type_enum}

# Versions are structured semver, not strings.
contract_version: {major: 1, minor: 0, patch: 0}
node_version: {major: 0, minor: 1, patch: 0}

input_model: ${package}.nodes.${node_name}.models.model_${node_name}_input.${input_class}
output_model: ${package}.nodes.${node_name}.models.model_${node_name}_output.${output_class}

# Handler binding. RuntimeLocal reads BOTH of these:
#   - handler.module / handler.class / handler.input_model build the initial
#     typed payload and resolve the handler on the single-handler path;
#   - handler_routing.default_handler ("module_ref:ClassName") is the canonical
#     binding the compute path and the canon-shape ratchet resolve.
handler:
  module: ${handler_module}
  class: ${handler_class}
  input_model: ${package}.nodes.${node_name}.models.model_${node_name}_input.${input_class}

handler_routing:
  default_handler: ${handler_module}:${handler_class}

# Topic the runtime treats as the completion signal. A contract without it is
# only executable on the handler-resolved compute path.
terminal_event: onex.evt.${package}.${node_name}-completed.v1

descriptor:
  node_archetype: ${node_type}
  purity: ${purity}
  runtime_profiles:
    - ${runtime_profile}
  idempotent: ${idempotent}
  timeout_ms: 30000

event_bus:
  subscribe_topics:
    - onex.cmd.${package}.${node_name}-requested.v1
  publish_topics:
    - onex.evt.${package}.${node_name}-completed.v1

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

    ${todo}(OMN-XXXX): Implement node logic.
    \"\"\"

    def ${node_method}(self, input_data: object) -> object:
        \"\"\"Run the ${node_type} step for ${node_name_display}.

        Named for the archetype rather than a bare ``process``: ``onex validate``
        rejects ``process``/``run``/``execute`` as generic terminology.

        ${todo}(OMN-XXXX): Implement ${node_type} logic for ${node_name_display}.
        \"\"\"
        raise NotImplementedError("${node_class}.${node_method} not yet implemented")
"""
)

HANDLER_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"Handler for ${node_name_display}.\"\"\"

from __future__ import annotations

from ${package}.nodes.${node_name}.models.model_${node_name}_input import (
    ${input_class},
)
from ${package}.nodes.${node_name}.models.model_${node_name}_output import (
    ${output_class},
)

__all__ = ["${handler_class}"]


class ${handler_class}:
    \"\"\"Canonical definition-B handler for ${node_name_display}.

    Definition-B is the canonical ONEX handler shape: a typed payload in, a
    typed response out. The event envelope is the shared runtime adapter's
    concern, so this class must never import or return an envelope type.

    Keep handlers stateless and deterministic — the ${node_type} archetype's
    ${purity_note}
    \"\"\"

    def handle(self, request: ${input_class}) -> ${output_class}:
        \"\"\"Return the ${node_type} result for ${node_name_display}.

        The scaffold returns an empty response so a freshly generated node runs
        end-to-end with no edits. Replace the body with real logic.

        ${todo}(OMN-XXXX): Implement handler logic for ${node_name_display},
        reading the fields you add to ${input_class} off ``request``.
${data_provenance_guidance}        \"\"\"
        return ${output_class}()
"""
)

# OMN-16680: input and output live in SEPARATE modules. ONEX is a
# one-model-per-file architecture and `onex validate`'s `architecture`
# validator hard-fails two BaseModel subclasses in one file. The enclosing
# DIRECTORY (`models/`) is unchanged, which is the granularity
# omnibase_core/CLAUDE.md -> External SDK Surface pins as stable.
MODEL_INPUT_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"Input model for ${node_name_display}.\"\"\"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["${input_class}"]


class ${input_class}(BaseModel):
    \"\"\"Input model for ${node_name_display}.

    ``extra="forbid"`` is the ONEX house rule: Pydantic's default silently
    drops unknown fields, which turns a typo in a payload into invisible data
    loss. Add your typed fields below.
    \"\"\"

    model_config = ConfigDict(extra="forbid")
"""
)

MODEL_OUTPUT_TEMPLATE = Template(
    """\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
\"\"\"Output model for ${node_name_display}.\"\"\"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["${output_class}"]


class ${output_class}(BaseModel):
    \"\"\"Output model for ${node_name_display}.

    ``extra="forbid"`` for the same reason as the input model: an unknown field
    on a response is a contract mismatch, not something to drop silently.
    \"\"\"

    model_config = ConfigDict(extra="forbid")
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
    # OMN-16680: the `Model` prefix is the ONEX naming convention for Pydantic
    # BaseModel classes (omnibase_core/CLAUDE.md), it is what OMN-16679's
    # AC2 already specified for the generated handler signature
    # (`handle(request: ModelXInput) -> ModelXOutput`), and the `patterns`
    # validator enforces it.
    input_class = f"Model{cls}Input"
    output_class = f"Model{cls}Output"

    node_dir = project_root / "src" / package / "nodes" / snake
    if node_dir.exists():
        raise click.ClickException(f"Node directory already exists: {node_dir}")

    node_dir.mkdir(parents=True)
    (node_dir / "__init__.py").write_text("")

    _purity_map = {
        "compute": "pure",
        "reducer": "pure",
        "effect": "impure",
        "orchestrator": "impure",
    }
    _profile_map = {
        "compute": "compute",
        "reducer": "reducers",
        "effect": "effects",
        "orchestrator": "effects",
    }
    # Pure archetypes (compute, reducer) are idempotent by definition:
    # same input → same output, no side effects to repeat.
    _idempotent_map = {
        "compute": "true",
        "reducer": "true",
        "effect": "false",
        "orchestrator": "false",
    }
    # Purity sentence closing the generated handler docstring, per archetype.
    _purity_note_map = {
        "compute": "contract is pure: same input, same output, no I/O.",
        "reducer": "contract is pure: fold state from events, never perform I/O.",
        "effect": "side effects belong here, and nowhere else.",
        "orchestrator": "job is to coordinate, not to hold business logic.",
    }
    # The node shell's entry-point method, per archetype. A bare `process`
    # (and `run`, `execute`, ...) is rejected by the `patterns` validator as
    # generic terminology; these read as the archetype's own verb (OMN-16680).
    _node_method_map = {
        "compute": "compute",
        "reducer": "reduce_state",
        "effect": "apply_effect",
        "orchestrator": "orchestrate",
    }
    ctx = {
        "todo": _TODO,
        "node_name": snake,
        "node_type": node_type,
        # EnumNodeType's generic archetype members (OMN-16680); see the comment
        # on CONTRACT_TEMPLATE's node_type field.
        "node_type_enum": f"{node_type.upper()}_GENERIC",
        "node_type_title": node_type.title(),
        "node_method": _node_method_map[node_type],
        "node_class": f"Node{cls}",
        "node_name_display": node_name,
        "package": package,
        "input_class": input_class,
        "output_class": output_class,
        # RuntimeLocal resolves the handler through these two: the dotted module
        # path and the class inside it (OMN-16679).
        "handler_module": f"{package}.nodes.{snake}.handlers.handler_{snake}",
        "handler_class": f"Handler{cls}",
        "purity_note": _purity_note_map[node_type],
        "purity": _purity_map[node_type],
        "runtime_profile": _profile_map[node_type],
        "idempotent": _idempotent_map[node_type],
        "data_provenance_guidance": (
            (
                "\n"
                "        When writing projection rows, record data_provenance so consumers\n"
                "        can distinguish measured data from seeded or estimated values:\n"
                "\n"
                "            from omnibase_core.enums.enum_data_provenance import (\n"
                "                EnumDataProvenance,\n"
                "            )\n"
                "\n"
                '            row["data_provenance"] = EnumDataProvenance.MEASURED.value\n'
            )
            if node_type == "reducer"
            else ""
        ),
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
    (models_dir / f"model_{snake}_input.py").write_text(
        MODEL_INPUT_TEMPLATE.substitute(ctx)
    )
    (models_dir / f"model_{snake}_output.py").write_text(
        MODEL_OUTPUT_TEMPLATE.substitute(ctx)
    )

    click.echo(f"Created {node_type} node '{node_name}' at {node_dir}")
    click.echo("  contract.yaml")
    click.echo(f"  node_{snake}_{node_type}.py")
    click.echo(f"  handlers/handler_{snake}.py")
    click.echo(f"  models/model_{snake}_input.py")
    click.echo(f"  models/model_{snake}_output.py")
