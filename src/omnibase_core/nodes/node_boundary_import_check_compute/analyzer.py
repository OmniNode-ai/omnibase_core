# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure symbol-level extraction for Python imports, strings and YAML (OMN-17427).

Only ``src/<pkg>/nodes/node_*/`` directories are local nodes. Foreign node
roots and internals count, except the explicit core base-class modules.
Seam class is a heuristic routing hint reviewed per seam, not a prescription:
exceptions and known plain dataclasses are shared models, not protocols.
No suppression or allowlist changes the observed symbol identities.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Final, Literal

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

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
CORE_BASE_CLASS_MODULES: Final = (
    "node_compute",
    "node_effect",
    "node_orchestrator",
    "node_reducer",
    "node_service_compute",
    "node_service_effect",
    "node_service_orchestrator",
    "node_service_reducer",
)
EXCLUDED_SEGMENTS: Final = frozenset({"tests", "test"})
ROOT_EXCLUDED_SEGMENTS: Final = frozenset(
    {"archived", "archive", "workspace", "build", "dist", "node_modules", ".venv"}
)
_MODULE_REFERENCE: Final = re.compile(
    rf"(?:{'|'.join(REGISTRY_PACKAGES)})\.nodes\.node_\w+(?:\.\w+)*(?::\w+)?"
)
_NAME_SEAMS: Final[tuple[tuple[str, Literal["model", "protocol"]], ...]] = (
    ("Model", "model"),
    ("Enum", "model"),
    ("Protocol", "protocol"),
)


def eligible_importer(path: str, packages: tuple[str, ...] = ()) -> bool:
    """Scan Python anywhere and YAML under src/<pkg>, with precise exclusions."""
    parsed = PurePosixPath(path)
    parts = parsed.parts
    if (
        not parts
        or parts[0] in ROOT_EXCLUDED_SEGMENTS
        or EXCLUDED_SEGMENTS.intersection(parts)
    ):
        return False
    return parsed.suffix == ".py" or (
        parsed.suffix in {".yaml", ".yml"}
        and len(parts) >= 3
        and parts[0] == "src"
        and parts[1] in packages
    )


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
    """Discover only node directories directly inside a package's nodes folder."""
    parts = PurePosixPath(path).parts
    if (
        len(parts) >= 5
        and parts[0] == "src"
        and parts[1] in packages
        and parts[2] == "nodes"
        and parts[3].startswith("node_")
    ):
        return (".".join(parts[1:4]),)
    return ()


def _node_of(module: str, nodes: set[str], *, foreign: bool = False) -> str | None:
    parts = module.split(".")
    if len(parts) < 3 or parts[1] != "nodes" or not parts[2].startswith("node_"):
        return None
    if parts[0] == "omnibase_core" and parts[2] in CORE_BASE_CLASS_MODULES:
        return None
    candidate = ".".join(parts[:3])
    return candidate if foreign or candidate in nodes else None


def _seam(
    target: str,
    node: str,
    name: str,
    importer_in_node: bool,
    plain_dataclass: bool = False,
) -> Literal["model", "protocol", "contract", "event"]:
    if name.endswith(("Error", "Exception")) or plain_dataclass:
        return "model"
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
            f"{base}.{alias.name}"
            if (
                f"{base}.{alias.name}" in known_modules
                or (base.endswith(".nodes") and alias.name.startswith("node_"))
                or (alias.name.startswith("_") and not alias.name.startswith("__"))
            )
            else base,
            alias.name,
        )
        for alias in statement.names
    ]


def _reference(value: str) -> tuple[str, str] | None:
    if not _MODULE_REFERENCE.fullmatch(value):
        return None
    target, _, name = value.partition(":")
    return target, name


def _yaml_values(node: Node, visited: set[int]) -> Iterator[ScalarNode]:
    """Walk values, excluding mapping keys and terminating recursive aliases."""
    if id(node) in visited:
        return
    visited.add(id(node))
    if isinstance(node, ScalarNode):
        if node.tag == "tag:yaml.org,2002:str":
            yield node
    elif isinstance(node, MappingNode):
        for _, value in node.value:
            yield from _yaml_values(value, visited)
    elif isinstance(node, SequenceNode):
        for value in node.value:
            yield from _yaml_values(value, visited)


def _dataclasses(tree: ast.Module) -> set[str]:
    """Recognize plain dataclass declarations, including decorator aliases."""
    decorators = {"dataclass", "dataclasses.dataclass"}
    for item in ast.walk(tree):
        if isinstance(item, ast.ImportFrom) and item.module == "dataclasses":
            decorators.update(
                alias.asname or alias.name
                for alias in item.names
                if alias.name == "dataclass"
            )
        elif isinstance(item, ast.Import):
            decorators.update(
                f"{alias.asname or alias.name}.dataclass"
                for alias in item.names
                if alias.name == "dataclasses"
            )
    return {
        item.name
        for item in tree.body
        if isinstance(item, ast.ClassDef)
        and any(
            ast.unparse(
                decorator.func if isinstance(decorator, ast.Call) else decorator
            )
            in decorators
            for decorator in item.decorator_list
        )
    }


def extract_edges(
    request: ModelBoundaryImportCheckInput,
) -> tuple[
    tuple[ModelBoundaryImportEdge, ...], tuple[ModelValidationFindingEmbed, ...]
]:
    """Observe unique symbol triples; the earliest reference wins per identity.

    Every imported name is retained. YAML values and entire Python string
    constants use the same boundary and seam rules as static imports.
    """
    known_modules = set(request.known_modules)
    nodes = set(request.node_packages)
    for file in request.files:
        if PurePosixPath(file.path).suffix == ".py":
            known_modules.add(module_name(file.path, request.repo_packages))
        nodes.update(node_directories(file.path, request.repo_packages))
    edges: dict[str, ModelBoundaryImportEdge] = {}
    errors: list[ModelValidationFindingEmbed] = []
    dataclasses: set[tuple[str, str]] = set()
    references: dict[
        str, list[tuple[str, str, int, Literal["import", "yaml", "string"]]]
    ] = {}
    for file in sorted(request.files, key=lambda file: file.path):
        if not eligible_importer(file.path, request.repo_packages):
            continue
        is_python = PurePosixPath(file.path).suffix == ".py"
        importer = (
            module_name(file.path, request.repo_packages) if is_python else file.path
        )
        refs: list[tuple[str, str, int, Literal["import", "yaml", "string"]]] = []
        try:
            if is_python:
                tree = ast.parse(file.source, filename=file.path)
                dataclasses.update((importer, name) for name in _dataclasses(tree))
                for item in sorted(
                    ast.walk(tree),
                    key=lambda item: (
                        getattr(item, "lineno", 0),
                        getattr(item, "col_offset", 0),
                    ),
                ):
                    if isinstance(item, (ast.Import, ast.ImportFrom)):
                        refs.extend(
                            (target, name, item.lineno, "import")
                            for target, name in _import_pairs(
                                item, importer, file.path, known_modules
                            )
                        )
                    elif isinstance(item, ast.Constant) and isinstance(item.value, str):
                        reference = _reference(item.value)
                        if reference:
                            refs.append((*reference, item.lineno, "string"))
            else:
                for document in yaml.compose_all(file.source, Loader=yaml.SafeLoader):
                    if document is not None:
                        for value in _yaml_values(document, set()):
                            reference = _reference(value.value)
                            if reference:
                                refs.append(
                                    (*reference, value.start_mark.line + 1, "yaml")
                                )
        except (SyntaxError, ValueError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="unparseable-file",
                    location=file.path,
                    message=f"{file.path}: unparseable {'Python' if is_python else 'YAML'}: {exc}",
                )
            )
            continue
        references[file.path] = refs
    for file in sorted(request.files, key=lambda file: file.path):
        is_python = PurePosixPath(file.path).suffix == ".py"
        importer = (
            module_name(file.path, request.repo_packages) if is_python else file.path
        )
        directories = node_directories(file.path, request.repo_packages)
        importer_node = directories[0] if directories else None
        for target, name, line, via in sorted(
            references.get(file.path, []), key=lambda ref: ref[2]
        ):
            top = target.split(".")[0]
            foreign = top not in request.repo_packages
            if foreign and top not in REGISTRY_PACKAGES:
                continue
            target_node = _node_of(target, nodes, foreign=foreign)
            kind: Literal[
                "outside->node", "node->node", "cross-repo->node", "cross-repo-private"
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
                seam = _seam(
                    target,
                    target_node,
                    name,
                    importer_node is not None,
                    (target, name) in dataclasses,
                )
            elif foreign and any(
                part.startswith("_") and not part.startswith("__")
                for part in target.split(".")
            ):
                kind, seam = "cross-repo-private", "private-api"
            else:
                continue
            edge = ModelBoundaryImportEdge(
                importer=importer,
                importer_path=file.path,
                line=line,
                target=target,
                kind=kind,
                seam=seam,
                imported_name=name,
                via=via,
            )
            edges.setdefault(edge.identity, edge)
    return tuple(edges[key] for key in sorted(edges)), tuple(errors)


def parse_baseline(source: str, path: str) -> tuple[str, ...]:
    """Reject invalid schema and duplicate YAML keys before using edge state."""
    document = load_yaml_mapping_no_duplicates(source, source=path)
    return tuple(ModelBoundaryImportBaseline.model_validate(document).edges)


def render_baseline(edges: tuple[str, ...]) -> str:
    """Render the required sorted YAML document, including SPDX headers.

    One entry per line, never wrapped, so retiring an edge deletes one line.
    """
    document = ModelBoundaryImportBaseline(
        schema_version=2, gate="OMN-17427", edges=sorted(set(edges))
    )
    return (
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
        + yaml.safe_dump(
            document.model_dump(mode="json"), sort_keys=False, width=1_000_000
        )
    )
