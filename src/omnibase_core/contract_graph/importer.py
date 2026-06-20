# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Manifest-driven import + round-trip for the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

Read-only entry points:

- ``discover_contract_paths`` — manifest-driven discovery of ``contract.yaml``
  files under given roots, EXCLUDING ``.venv``, ``omni_worktrees``, and generated
  surfaces. Deterministically ordered.
- ``import_paths`` — import a set of node + UI component contracts into one
  ``ModelContractGraphIr`` with embedded source hashes + adapter version hashes.
- ``normalize_node_contract`` / ``normalize_ui_component`` — the canonical
  normalized contract form a round-trip targets. The semantic baseline against
  which a no-op round-trip is compared via ``cli_contract_diff``.
- ``round_trip_zero_diff`` — proves a no-op IR round-trip produces zero semantic
  diff for one imported source, using the shipped ``cli_contract_diff`` spine.

STRICTLY READ-ONLY: no source mutation, no contract authoring.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.cli.cli_contract_diff import (
    categorize_diff_entries,
    diff_contract_dicts,
    load_contract_yaml_file,
)
from omnibase_core.contract_graph.adapter_node_contract import (
    _ROLE_TO_CANONICAL_NODE_TYPE,
    import_node_contract,
    round_trip_node_node,
)
from omnibase_core.contract_graph.adapter_ui_component import (
    import_ui_component,
    round_trip_ui_component,
)
from omnibase_core.contract_graph.canonical_hash import canonicalize_contract
from omnibase_core.models.cli.model_diff_result import ModelDiffResult
from omnibase_core.models.contract_graph.model_contract_graph_edge import (
    ModelContractGraphEdge,
)
from omnibase_core.models.contract_graph.model_contract_graph_ir import (
    ModelContractGraphIr,
)
from omnibase_core.models.contract_graph.model_contract_graph_node import (
    ModelContractGraphNode,
)
from omnibase_core.models.contract_graph.model_contract_graph_source_set import (
    ModelContractGraphSourceSet,
)
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_json import JsonType

__all__ = [
    "IR_SCHEMA_VERSION",
    "EXCLUDED_DISCOVERY_DIRS",
    "discover_contract_paths",
    "normalize_node_contract",
    "normalize_ui_component",
    "import_node_path",
    "import_ui_component_instance",
    "import_paths",
    "round_trip_node_diff",
    "round_trip_ui_component_diff",
    "round_trip_zero_diff",
]

# Schema version of the Contract Graph IR this importer emits.
IR_SCHEMA_VERSION = ModelSemVer(major=0, minor=1, patch=0)

# Directory names excluded from manifest-driven discovery: virtualenvs, the
# worktrees tree, build/generated surfaces, and VCS internals. Discovery must
# not pick up vendored or generated contracts.
EXCLUDED_DISCOVERY_DIRS: frozenset[str] = frozenset(
    {
        ".venv",
        "venv",
        "omni_worktrees",
        ".git",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "generated",
        "_generated",
    }
)


def discover_contract_paths(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    """Discover ``contract.yaml`` files under ``roots``, deterministically ordered.

    Any path containing an excluded directory component (``.venv``,
    ``omni_worktrees``, generated surfaces, etc.) is skipped. The result is
    sorted by string path so two scans over the same tree yield identical order.
    """
    found: list[Path] = []
    for root in roots:
        for candidate in root.rglob("contract.yaml"):
            if any(part in EXCLUDED_DISCOVERY_DIRS for part in candidate.parts):
                continue
            found.append(candidate)
    return tuple(sorted(found, key=str))


def _load_yaml(path: Path) -> dict[str, JsonType]:
    """Load a contract YAML file via the shipped cli_contract_diff loader.

    Reuses ``load_contract_yaml_file`` from the contract-diff spine (path
    security checks + dict-root validation) rather than calling ``yaml.safe_load``
    directly — same loader the semantic-diff path uses, so import and diff read
    contracts identically.
    """
    return load_contract_yaml_file(path)


def _json_str_list(values: list[str]) -> list[JsonType]:
    """Widen a list of strings to ``list[JsonType]`` (str is a JsonType primitive).

    Per-element widening so a ``list[str]`` can be stored in a ``dict[str,
    JsonType]`` without an invariance error and without ``cast``.
    """
    widened: list[JsonType] = []
    for value in values:
        widened.append(value)
    return widened


def normalize_node_contract(
    data: dict[str, JsonType],
    source_path: str | None = None,
) -> dict[str, JsonType]:
    """Canonical normalized form of a backend node contract.

    The semantic projection a node-contract round-trip targets: handler_id,
    name, node_type (always canonical lowercase), sorted publish/subscribe
    topics (from both top-level and ``event_bus:`` section), and input/output
    models.

    This is the baseline a no-op round-trip is diffed against — NOT the raw
    source (which also carries ``descriptor`` / ``state_transitions`` /
    ``workflow_coordination`` / version/build noise the IR drops).

    ``source_path`` is used as the node_id fallback when the contract declares
    no ``handler_id``, ``name``, or ``node_id`` (state_machine /
    workflow_coordination dialect contracts in ``contracts/runtime/``).
    """
    from omnibase_core.contract_graph.adapter_node_contract import (
        _NODE_TYPE_TO_ROLE,  # late import: avoids circular at module level
        _node_id_from_source_path,  # late import: avoids circular at module level
    )

    canonical = canonicalize_contract(data)
    handler_id = canonical.get("handler_id")
    name = canonical.get("name")
    node_id_field = canonical.get("node_id")
    node_id: str | None = (
        handler_id
        if isinstance(handler_id, str) and handler_id
        else (
            name
            if isinstance(name, str) and name
            else (
                node_id_field
                if isinstance(node_id_field, str) and node_id_field
                else None
            )
        )
    )
    if node_id is None:
        if source_path is not None:
            node_id = _node_id_from_source_path(source_path)
        else:
            raise ValueError(  # error-ok: input validation at the contract-import boundary
                "node contract has no handler_id, name, or node_id, and no source_path was provided"
            )

    node_type_raw = canonical.get("node_type")
    if not isinstance(node_type_raw, str):
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            "node contract has no string node_type"
        )
    # Normalize UPPER_GENERIC tokens to canonical lowercase for the round-trip
    # baseline so a REDUCER_GENERIC source round-trips to "reducer" — the same
    # token round_trip_node_node emits.
    if node_type_raw in _NODE_TYPE_TO_ROLE:
        role = _NODE_TYPE_TO_ROLE[node_type_raw]
        node_type_canonical: str = _ROLE_TO_CANONICAL_NODE_TYPE.get(role, node_type_raw)
    else:
        node_type_canonical = node_type_raw

    result: dict[str, JsonType] = {
        "handler_id": node_id,
        "name": name if isinstance(name, str) and name else node_id,
        "node_type": node_type_canonical,
    }

    # Extract topics from both top-level fields and nested event_bus: section
    # (event_bus dialect). Union is taken when both are present.
    def _collect_topics(key: str) -> list[str]:
        top = canonical.get(key)
        top_list: list[str] = (
            [str(x) for x in top if isinstance(x, str)] if isinstance(top, list) else []
        )
        event_bus = canonical.get("event_bus")
        nested_list: list[str] = []
        if isinstance(event_bus, dict):
            nested = event_bus.get(key)
            if isinstance(nested, list):
                nested_list = [str(x) for x in nested if isinstance(x, str)]
        seen: set[str] = set(top_list)
        combined: list[str] = list(top_list)
        for t in nested_list:
            if t not in seen:
                combined.append(t)
                seen.add(t)
        return sorted(combined)

    publish = _collect_topics("publish_topics")
    if publish:
        result["publish_topics"] = _json_str_list(publish)
    subscribe = _collect_topics("subscribe_topics")
    if subscribe:
        result["subscribe_topics"] = _json_str_list(subscribe)

    input_model = canonical.get("input_model")
    if isinstance(input_model, str):
        result["input_model"] = input_model
    output_model = canonical.get("output_model")
    if isinstance(output_model, str):
        result["output_model"] = output_model
    return result


def normalize_ui_component(contract: ModelComponentContract) -> dict[str, JsonType]:
    """Canonical normalized form of a UI component contract.

    The semantic projection a component round-trip targets: component id, title,
    sorted command topics emitted, sorted projection topics bound.
    """
    result: dict[str, JsonType] = {
        "component_id": contract.component_id,
        "title": contract.title,
    }
    emits = _json_str_list(sorted(a.command_topic for a in contract.actions))
    if emits:
        result["action_command_topics"] = emits
    binds = _json_str_list(sorted(b.projection_topic for b in contract.data_bindings))
    if binds:
        result["data_binding_projection_topics"] = binds
    return result


def import_node_path(
    path: Path,
    repo_relative: str,
) -> tuple[ModelContractGraphNode, tuple[ModelContractGraphEdge, ...]]:
    """Load + import one backend node contract file into IR node + edges."""
    data = _load_yaml(path)
    return import_node_contract(data, repo_relative)


def import_ui_component_instance(
    contract: ModelComponentContract,
    source_path: str,
) -> tuple[ModelContractGraphNode, tuple[ModelContractGraphEdge, ...]]:
    """Import one UI component contract instance into IR node + edges."""
    return import_ui_component(contract, source_path)


def import_paths(
    discovery_roots: tuple[str, ...],
    node_paths: tuple[tuple[Path, str], ...],
    ui_components: tuple[tuple[ModelComponentContract, str], ...],
) -> ModelContractGraphIr:
    """Import node-contract files + UI component contracts into one IR.

    ``node_paths`` are ``(filesystem_path, repo_relative_path)`` pairs;
    ``ui_components`` are ``(contract, source_path)`` pairs. Nodes, edges, and the
    source set are deterministically ordered so two imports over identical inputs
    yield identical IR.
    """
    nodes: list[ModelContractGraphNode] = []
    edges: list[ModelContractGraphEdge] = []

    for fs_path, repo_relative in node_paths:
        node, node_edges = import_node_path(fs_path, repo_relative)
        nodes.append(node)
        edges.extend(node_edges)

    for contract, source_path in ui_components:
        node, node_edges = import_ui_component_instance(contract, source_path)
        nodes.append(node)
        edges.extend(node_edges)

    nodes.sort(key=lambda n: n.node_id)
    edges.sort(key=lambda e: e.edge_id)

    refs = tuple(sorted((n.source_ref for n in nodes), key=lambda r: r.source_path))
    source_set = ModelContractGraphSourceSet(
        discovery_roots=discovery_roots,
        refs=refs,
    )
    return ModelContractGraphIr(
        ir_version=IR_SCHEMA_VERSION,
        nodes=tuple(nodes),
        edges=tuple(edges),
        source_set=source_set,
    )


def _edges_for(
    ir: ModelContractGraphIr, node_id: str
) -> tuple[ModelContractGraphEdge, ...]:
    """All IR edges sourced from ``node_id``."""
    return tuple(e for e in ir.edges if e.source_node_id == node_id)


def round_trip_node_diff(
    ir: ModelContractGraphIr,
    node_id: str,
    source: dict[str, JsonType],
) -> ModelDiffResult:
    """Diff a node's no-op round-trip against its normalized source.

    Round-trips the IR node + its edges back to canonical normalized node form
    and compares it to ``normalize_node_contract(source)`` using the shipped
    semantic diff spine.

    The IR node's ``source_ref.source_path`` is passed to
    ``normalize_node_contract`` so that state_machine / workflow_coordination
    dialect contracts (which declare no ``handler_id`` or ``name``) resolve
    their node_id from the file path stem, matching what ``import_node_contract``
    already does.
    """
    node = next(n for n in ir.nodes if n.node_id == node_id)
    round_tripped = round_trip_node_node(node, _edges_for(ir, node_id))
    baseline = normalize_node_contract(source, source_path=node.source_ref.source_path)
    diffs = diff_contract_dicts(baseline, round_tripped)
    return categorize_diff_entries(diffs)


def round_trip_ui_component_diff(
    ir: ModelContractGraphIr,
    contract: ModelComponentContract,
) -> ModelDiffResult:
    """Diff a component's no-op round-trip against its normalized source."""
    node = next(n for n in ir.nodes if n.node_id == contract.component_id)
    round_tripped = round_trip_ui_component(node, _edges_for(ir, contract.component_id))
    baseline = normalize_ui_component(contract)
    diffs = diff_contract_dicts(baseline, round_tripped)
    return categorize_diff_entries(diffs)


def round_trip_zero_diff(diff_result: ModelDiffResult) -> bool:
    """True if a round-trip diff result carries zero semantic changes."""
    return not diff_result.has_changes
