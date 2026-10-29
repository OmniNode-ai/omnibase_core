# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Test-side copy of the omnimarket renderer (the renderer stays in omnimarket, it is not a validator).

The diagram-drift checker takes a fragment loader; this copy is the fixture renderer that reproduces
the merged node's verdicts on the merged task's fixtures.

``render_contract_diagram``: a contract fragment's text to Mermaid, by fixed structural rules.

State machine: ``stateDiagram-v2``; ``[*] --> <initial_state>``; one line per transition in
contract order, ``<from> --> <to> : <trigger>`` followed by `` (priority N)`` when the priority is
not 0 and by `` [<expression> and <expression>]`` when the transition has conditions; one
``<terminal> --> [*]`` line per terminal state in contract order.

Graph: ``flowchart TB``; one line per node in contract order, ``id["description"]`` for a node
whose type is not ``COMPUTE_GENERIC`` and ``id("description")`` for one that is; one
``dep --> id`` line per ``depends_on`` edge in contract order. The collapsed view omits each
``COMPUTE_GENERIC`` node with one predecessor and one successor and draws it as the label of the
arrow from its predecessor to its successor; the plain edges come first, then the labelled ones.
A compute node whose predecessor or successor is itself such a node stays a node, because
collapsing a chain would leave an arrow with no end.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, JsonValue

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.model_contract_workflow_definition import (
    ModelContractWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.diagram_drift.model_loaded_diagram_fragment import (
    ModelLoadedDiagramFragment,
)

EnumDiagramView = Literal["full", "collapsed"]
EnumDiagramKind = Literal["state_machine", "graph"]


class ModelLoadedFragment(BaseModel):
    """A fragment the core model accepted, kept as the raw mapping the file holds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumDiagramKind
    initial_state: str = ""
    terminal_states: tuple[str, ...] = ()
    transitions: tuple[dict[str, JsonValue], ...] = ()
    nodes: tuple[dict[str, JsonValue], ...] = ()


_COMPUTE = "COMPUTE_GENERIC"
_INDENT = "    "


def _mapping(value: JsonValue, where: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a mapping")
    return value


def _entries(value: JsonValue, where: str) -> tuple[dict[str, JsonValue], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a list")
    return tuple(_mapping(item, f"an entry of {where}") for item in value)


def load_fragment(fragment_text: str) -> ModelLoadedFragment:
    """Validate a fragment with the core model and keep the raw mapping the generator draws from."""
    try:
        return _load_fragment(fragment_text)
    except (ModelOnexError, yaml.YAMLError) as refused:
        # The core models raise their own error type; callers see one refusal type.
        raise ValueError(str(refused)) from refused


def _load_fragment(fragment_text: str) -> ModelLoadedFragment:
    document = yaml.safe_load(fragment_text)
    root = _mapping(document, "the fragment")
    if "state_machine" in root:
        machine = _mapping(root["state_machine"], "state_machine")
        ModelFSMSubcontract.model_validate(machine)
        terminals = machine.get("terminal_states", [])
        if not isinstance(terminals, list):
            raise ValueError("state_machine.terminal_states must be a list")
        return ModelLoadedFragment(
            kind="state_machine",
            initial_state=str(machine["initial_state"]),
            terminal_states=tuple(str(t) for t in terminals),
            transitions=_entries(machine["transitions"], "state_machine.transitions"),
        )
    coordination = root.get("workflow_coordination")
    if isinstance(coordination, dict) and "workflow_definition" in coordination:
        definition = _mapping(
            coordination["workflow_definition"],
            "workflow_coordination.workflow_definition",
        )
        ModelContractWorkflowDefinition.model_validate(definition)
        graph = _mapping(definition["execution_graph"], "execution_graph")
        return ModelLoadedFragment(
            kind="graph",
            nodes=_entries(graph["nodes"], "execution_graph.nodes"),
        )
    raise ValueError(
        "a fragment holds a state_machine or a workflow_coordination.workflow_definition"
    )


def _label(text: str) -> str:
    return text.replace('"', "#quot;")


def _render_state_machine(fragment: ModelLoadedFragment) -> str:
    lines = ["stateDiagram-v2", f"{_INDENT}[*] --> {fragment.initial_state}"]
    for transition in fragment.transitions:
        line = f"{_INDENT}{transition['from_state']} --> {transition['to_state']} : {transition['trigger']}"
        priority = transition.get("priority", 0)
        if priority != 0:
            line += f" (priority {priority})"
        conditions = transition.get("conditions") or []
        if isinstance(conditions, list) and conditions:
            expressions = [
                str(_mapping(c, "a condition")["expression"]) for c in conditions
            ]
            line += f" [{' and '.join(expressions)}]"
        lines.append(line)
    lines.extend(f"{_INDENT}{state} --> [*]" for state in fragment.terminal_states)
    return "\n".join(lines) + "\n"


def _depends_on(node: dict[str, JsonValue]) -> list[str]:
    raw = node.get("depends_on") or []
    return [str(dep) for dep in raw] if isinstance(raw, list) else []


def _node_line(node: dict[str, JsonValue]) -> str:
    node_id = str(node["node_id"])
    label = _label(str(node.get("description") or node_id))
    if node.get("node_type") == _COMPUTE:
        return f'{_INDENT}{node_id}("{label}")'
    return f'{_INDENT}{node_id}["{label}"]'


def _collapsible(nodes: tuple[dict[str, JsonValue], ...]) -> dict[str, str]:
    """Omitted node id to its successor id."""
    successors: dict[str, list[str]] = {str(n["node_id"]): [] for n in nodes}
    for node in nodes:
        for dep in _depends_on(node):
            successors[dep].append(str(node["node_id"]))
    candidates = {
        str(n["node_id"]): successors[str(n["node_id"])][0]
        for n in nodes
        if n.get("node_type") == _COMPUTE
        and len(_depends_on(n)) == 1
        and len(successors[str(n["node_id"])]) == 1
    }
    preds = {str(n["node_id"]): _depends_on(n) for n in nodes}
    return {
        node_id: successor
        for node_id, successor in candidates.items()
        if preds[node_id][0] not in candidates and successor not in candidates
    }


def _render_graph(fragment: ModelLoadedFragment, view: EnumDiagramView) -> str:
    omitted = _collapsible(fragment.nodes) if view == "collapsed" else {}
    lines = ["flowchart TB"]
    lines.extend(
        _node_line(n) for n in fragment.nodes if str(n["node_id"]) not in omitted
    )
    for node in fragment.nodes:
        node_id = str(node["node_id"])
        if node_id in omitted:
            continue
        lines.extend(
            f"{_INDENT}{dep} --> {node_id}"
            for dep in _depends_on(node)
            if dep not in omitted
        )
    for node in fragment.nodes:
        node_id = str(node["node_id"])
        if node_id in omitted:
            label = _label(str(node.get("description") or node_id))
            lines.append(
                f'{_INDENT}{_depends_on(node)[0]} -- "{label}" --> {omitted[node_id]}'
            )
    return "\n".join(lines) + "\n"


def render_loaded_fragment(fragment: ModelLoadedFragment, view: EnumDiagramView) -> str:
    """The Mermaid text of a loaded fragment; a state machine has only the full view."""
    if fragment.kind == "state_machine":
        if view != "full":
            raise ValueError("a state machine has only the full view")
        return _render_state_machine(fragment)
    return _render_graph(fragment, view)


def load_fixture_fragment(fragment_text: str) -> ModelLoadedDiagramFragment:
    """The caller-side loader: the fixture renderer's drawing of each view the fragment kind offers."""
    fragment = load_fragment(fragment_text)
    views: tuple[EnumDiagramView, ...] = (
        ("full",) if fragment.kind == "state_machine" else ("full", "collapsed")
    )
    return ModelLoadedDiagramFragment(
        kind=fragment.kind,
        drawings={view: render_loaded_fragment(fragment, view) for view in views},
    )
