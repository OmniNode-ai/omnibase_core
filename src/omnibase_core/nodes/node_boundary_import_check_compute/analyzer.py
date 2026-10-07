# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure AST boundary extraction and baseline serialization (OMN-17427).

Local nodes are directories, inferred from path directory components or an
explicit EFFECT inventory; ``nodes/node_effect.py`` is never a node. Foreign
trees cannot be inspected: ``pkg.nodes.node_x`` alone is ambiguous with a
base-class module and is not a node edge. A further dotted segment is required.
This ports the scratch tangle scan with the ticket's imported-name-first seam
precedence, registry tuple, tracked importer scope and POSIX path keys.
"""

from __future__ import annotations

import ast
from pathlib import PurePosixPath
from typing import Final, Literal

import yaml

from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_baseline import (
    ModelBoundaryImportBaseline,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_input import (
    ModelBoundaryImportCheckInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_edge import (
    ModelBoundaryImportEdge,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

VALIDATOR_ID: Final = "node-boundary-imports"
DEFAULT_BASELINE: Final = ".onex_ratchets/node_boundary_import_baseline.yaml"
REGISTRY_PACKAGES: Final = (
    "omnibase_compat",
    "omnibase_core",
    "omnibase_spi",
    "omnibase_infra",
    "omnimarket",
    "omniclaude",
    "omniintelligence",
    "omnimemory",
    "omnibase_internal",
    "onex_change_control",
)
EXCLUDED_SEGMENTS: Final = frozenset(
    {
        "tests",
        "test",
        "archived",
        "archive",
        "workspace",
        "build",
        "dist",
        "node_modules",
        ".venv",
    }
)
_NAME_SEAMS: Final[tuple[tuple[str, Literal["model", "protocol"]], ...]] = (
    ("Model", "model"),
    ("Enum", "model"),
    ("Protocol", "protocol"),
)


def eligible_importer(path: str) -> bool:
    """Select every Python importer except the ticket's excluded segments."""
    parsed = PurePosixPath(path)
    return parsed.suffix == ".py" and not EXCLUDED_SEGMENTS.intersection(parsed.parts)


def module_name(path: str, packages: tuple[str, ...]) -> str:
    """Package initializers name their package; other surfaces retain paths."""
    parsed = PurePosixPath(path)
    parts = parsed.with_suffix("").parts
    if len(parts) >= 3 and parts[0] == "src" and parts[1] in packages:
        module_parts = parts[1:]
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        return ".".join(module_parts)
    return parsed.as_posix()


def node_directories(path: str, packages: tuple[str, ...]) -> tuple[str, ...]:
    """Discover nodes from directory components, never from a filename."""
    parts = PurePosixPath(path).parts
    if len(parts) < 3 or parts[0] != "src" or parts[1] not in packages:
        return ()
    directories = parts[1:-1]
    return tuple(
        ".".join(directories[: index + 2])
        for index in range(1, len(directories) - 1)
        if directories[index] == "nodes" and directories[index + 1].startswith("node_")
    )


def _node_of(module: str, nodes: set[str], *, foreign: bool = False) -> str | None:
    parts = module.split(".")
    for index in range(1, len(parts) - 1):
        if parts[index] == "nodes" and parts[index + 1].startswith("node_"):
            candidate = ".".join(parts[: index + 2])
            if (foreign and index + 2 < len(parts)) or candidate in nodes:
                return candidate
    return None


def _seam(
    target: str, node: str, name: str, importer_in_node: bool
) -> Literal["model", "protocol", "contract", "event"]:
    for prefix, seam in _NAME_SEAMS:
        if name.startswith(prefix):
            return seam
    if name.isupper():
        return "contract"
    sub = target[len(node) + 1 :].split(".")[0].lower() if target != node else ""
    if sub in {"models", "model", "enums", "types", "schemas", "dto"} or sub.startswith(
        ("model_", "enum_")
    ):
        return "model"
    if sub in {"protocols", "protocol", "ports"} or sub.startswith("protocol_"):
        return "protocol"
    if sub in {"contract", "contracts", "config"} or sub.startswith(
        ("constants", "topics")
    ):
        return "contract"
    return "event" if importer_in_node else "protocol"


def _import_pairs(
    statement: ast.Import | ast.ImportFrom,
    importer: str,
    path: str,
    known_modules: set[str],
) -> list[tuple[str, str]]:
    if isinstance(statement, ast.Import):
        return [(alias.name, "") for alias in statement.names]
    if statement.level:
        if "/" in importer or importer.endswith(".py"):
            return []
        parts = importer.split(".")
        if PurePosixPath(path).name != "__init__.py":
            parts = parts[:-1]
        if statement.level > len(parts):
            return []
        if statement.level > 1:
            parts = parts[: -(statement.level - 1)]
        base = ".".join(parts + ([statement.module] if statement.module else []))
    else:
        base = statement.module or ""
    return [
        (
            f"{base}.{alias.name}" if f"{base}.{alias.name}" in known_modules else base,
            alias.name,
        )
        for alias in statement.names
    ]


def extract_edges(
    request: ModelBoundaryImportCheckInput,
) -> tuple[
    tuple[ModelBoundaryImportEdge, ...], tuple[ModelValidationFindingEmbed, ...]
]:
    """Observe unique importer/target pairs and report every unparseable file.

    The earliest source line wins when multiple imported names share an edge,
    with source-order AST traversal making exports deterministic.
    """
    known_modules = set(request.known_modules)
    nodes = set(request.node_packages)
    for file in request.files:
        known_modules.add(module_name(file.path, request.repo_packages))
        nodes.update(node_directories(file.path, request.repo_packages))
    edges: dict[str, ModelBoundaryImportEdge] = {}
    errors: list[ModelValidationFindingEmbed] = []
    for file in sorted(request.files, key=lambda file: file.path):
        if not eligible_importer(file.path):
            continue
        importer = module_name(file.path, request.repo_packages)
        importer_node = _node_of(importer, nodes)
        try:
            tree = ast.parse(file.source, filename=file.path)
        except (SyntaxError, ValueError, UnicodeError) as exc:
            errors.append(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="unparseable-file",
                    location=file.path,
                    message=f"{file.path}: unparseable Python: {exc}",
                )
            )
            continue
        statements = sorted(
            (
                item
                for item in ast.walk(tree)
                if isinstance(item, (ast.Import, ast.ImportFrom))
            ),
            key=lambda item: (item.lineno, item.col_offset),
        )
        for statement in statements:
            for target, name in _import_pairs(
                statement, importer, file.path, known_modules
            ):
                top = target.split(".")[0]
                foreign = top not in request.repo_packages
                if foreign and top not in REGISTRY_PACKAGES:
                    continue
                target_node = _node_of(target, nodes, foreign=foreign)
                kind: Literal[
                    "outside->node",
                    "node->node",
                    "cross-repo->node",
                    "cross-repo-private",
                ]
                seam: Literal["model", "protocol", "contract", "event", "private-api"]
                if target_node and target_node != importer_node:
                    kind = (
                        "cross-repo->node"
                        if foreign
                        else "node->node"
                        if importer_node
                        else "outside->node"
                    )
                    seam = _seam(target, target_node, name, importer_node is not None)
                elif foreign and any(
                    part.startswith("_") and not part.startswith("__")
                    for part in target.split(".")
                ):
                    kind = "cross-repo-private"
                    seam = "private-api"
                else:
                    continue
                edge = ModelBoundaryImportEdge(
                    importer=importer,
                    importer_path=file.path,
                    line=statement.lineno,
                    target=target,
                    kind=kind,
                    seam=seam,
                    imported_name=name,
                )
                edges.setdefault(edge.identity, edge)
    return tuple(edges[key] for key in sorted(edges)), tuple(errors)


def parse_baseline(source: str, path: str) -> tuple[str, ...]:
    """Reject invalid schema and duplicate YAML keys before using edge state."""
    document = load_yaml_mapping_no_duplicates(source, source=path)
    return tuple(ModelBoundaryImportBaseline.model_validate(document).edges)


def render_baseline(edges: tuple[str, ...]) -> str:
    """Render the required sorted YAML document, including SPDX headers."""
    document = ModelBoundaryImportBaseline(
        schema_version=1, gate="OMN-17427", edges=sorted(set(edges))
    )
    return (
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
        + yaml.safe_dump(document.model_dump(mode="json"), sort_keys=False)
    )
