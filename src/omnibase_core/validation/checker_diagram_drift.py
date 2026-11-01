# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure diagram-drift checker: a document's text and a contract in, issues out (OMN-21510).

A diagram marker precedes a ``mermaid`` block and pairs by id with the fragment marker that
precedes a ``yaml`` block. The checker regenerates each diagram from its fragment and compares
it line by line. Marker syntax, drawing templates and diagnostics are parameters of
``diagram_drift.validation.yaml``; this module holds no rule data.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.model_contract_workflow_definition import (
    ModelContractWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.diagram_drift.model_diagram_block import ModelDiagramBlock
from omnibase_core.models.diagram_drift.model_diagram_drift_check_input import (
    ModelDiagramDriftCheckInput,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_check_result import (
    ModelDiagramDriftCheckResult,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_rules import (
    ModelDiagramDriftRules,
)
from omnibase_core.models.diagram_drift.model_diagram_fragment import (
    ModelDiagramFragment,
)
from omnibase_core.models.task_criteria.model_task_criteria_rule_row import (
    ModelTaskCriteriaRuleRow,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

if TYPE_CHECKING:
    from pydantic import JsonValue

__all__ = ["check_diagram_drift"]


def _fill(template: str, **fields: object) -> str:
    """Fill a contract template; a template naming an unknown field is a contract error."""
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError) as exc:
        raise ModelOnexError(
            message=f"rule template {template!r} cannot be filled: {exc!r}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from exc


def _refusal(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def _mapping(value: JsonValue, where: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise _refusal(f"{where} must be a mapping")
    return value


def _entries(value: JsonValue, where: str) -> tuple[dict[str, JsonValue], ...]:
    if not isinstance(value, list):
        raise _refusal(f"{where} must be a list")
    return tuple(_mapping(item, f"an entry of {where}") for item in value)


def _load_fragment(fragment_text: str) -> ModelDiagramFragment:
    """Validate a fragment with the core models and keep the raw mapping that is drawn."""
    try:
        root = _mapping(
            cast(
                "JsonValue",
                load_yaml_mapping_no_duplicates(fragment_text, source="the fragment"),
            ),
            "the fragment",
        )
        if "state_machine" in root:
            machine = _mapping(root["state_machine"], "state_machine")
            ModelFSMSubcontract.model_validate(machine)
            terminals = machine.get("terminal_states", [])
            if not isinstance(terminals, list):
                raise _refusal("state_machine.terminal_states must be a list")
            return ModelDiagramFragment(
                kind="state_machine",
                initial_state=str(machine["initial_state"]),
                terminal_states=tuple(str(t) for t in terminals),
                transitions=_entries(
                    machine["transitions"], "state_machine.transitions"
                ),
                nodes=(),
            )
        coordination = root.get("workflow_coordination")
        if isinstance(coordination, dict) and "workflow_definition" in coordination:
            definition = _mapping(
                coordination["workflow_definition"],
                "workflow_coordination.workflow_definition",
            )
            ModelContractWorkflowDefinition.model_validate(definition)
            graph = _mapping(definition["execution_graph"], "execution_graph")
            return ModelDiagramFragment(
                kind="graph",
                initial_state="",
                terminal_states=(),
                transitions=(),
                nodes=_entries(graph["nodes"], "execution_graph.nodes"),
            )
        raise _refusal(
            "a fragment holds a state_machine or a workflow_coordination.workflow_definition"
        )
    except (yaml.YAMLError, ValueError) as refused:
        # YAML and duplicate-key errors join the core models' error type: one refusal type.
        raise _refusal(str(refused)) from refused


def _label(row: ModelTaskCriteriaRuleRow, text: str) -> str:
    return text.replace(row.texts["quote"], row.texts["quote_entity"])


def _depends_on(node: dict[str, JsonValue]) -> list[str]:
    raw = node.get("depends_on") or []
    return [str(dep) for dep in raw] if isinstance(raw, list) else []


def _render_state_machine(
    row: ModelTaskCriteriaRuleRow, fragment: ModelDiagramFragment
) -> str:
    indent = row.texts["indent"]
    lines = [
        row.texts["state_header"],
        indent + _fill(row.texts["initial_line"], initial=fragment.initial_state),
    ]
    for transition in fragment.transitions:
        line = _fill(
            row.texts["transition_line"],
            source=transition["from_state"],
            target=transition["to_state"],
            trigger=transition["trigger"],
        )
        priority = transition.get("priority", 0)
        if priority != 0:
            line += _fill(row.texts["priority_suffix"], priority=priority)
        conditions = transition.get("conditions") or []
        if isinstance(conditions, list) and conditions:
            expressions = [
                str(_mapping(c, "a condition")["expression"]) for c in conditions
            ]
            line += _fill(
                row.texts["conditions_suffix"],
                expressions=row.texts["condition_join"].join(expressions),
            )
        lines.append(indent + line)
    lines.extend(
        indent + _fill(row.texts["terminal_line"], state=state)
        for state in fragment.terminal_states
    )
    return "\n".join(lines) + "\n"


def _node_line(row: ModelTaskCriteriaRuleRow, node: dict[str, JsonValue]) -> str:
    node_id = str(node["node_id"])
    label = _label(row, str(node.get("description") or node_id))
    template = (
        row.texts["compute_node_line"]
        if node.get("node_type") == row.texts["compute_node_type"]
        else row.texts["node_line"]
    )
    return row.texts["indent"] + _fill(template, id=node_id, label=label)


def _collapsible(
    row: ModelTaskCriteriaRuleRow, nodes: tuple[dict[str, JsonValue], ...]
) -> dict[str, str]:
    """Omitted node id to its successor id."""
    compute = row.texts["compute_node_type"]
    successors: dict[str, list[str]] = {str(n["node_id"]): [] for n in nodes}
    for node in nodes:
        for dep in _depends_on(node):
            successors[dep].append(str(node["node_id"]))
    candidates = {
        str(n["node_id"]): successors[str(n["node_id"])][0]
        for n in nodes
        if n.get("node_type") == compute
        and len(_depends_on(n)) == 1
        and len(successors[str(n["node_id"])]) == 1
    }
    preds = {str(n["node_id"]): _depends_on(n) for n in nodes}
    return {
        node_id: successor
        for node_id, successor in candidates.items()
        if preds[node_id][0] not in candidates and successor not in candidates
    }


def _render_graph(
    row: ModelTaskCriteriaRuleRow, fragment: ModelDiagramFragment, collapsed: bool
) -> str:
    indent = row.texts["indent"]
    omitted = _collapsible(row, fragment.nodes) if collapsed else {}
    lines = [row.texts["graph_header"]]
    lines.extend(
        _node_line(row, n) for n in fragment.nodes if str(n["node_id"]) not in omitted
    )
    for node in fragment.nodes:
        node_id = str(node["node_id"])
        if node_id in omitted:
            continue
        lines.extend(
            indent + _fill(row.texts["edge_line"], dep=dep, id=node_id)
            for dep in _depends_on(node)
            if dep not in omitted
        )
    for node in fragment.nodes:
        node_id = str(node["node_id"])
        if node_id in omitted:
            lines.append(
                indent
                + _fill(
                    row.texts["collapsed_edge_line"],
                    dep=_depends_on(node)[0],
                    label=_label(row, str(node.get("description") or node_id)),
                    successor=omitted[node_id],
                )
            )
    return "\n".join(lines) + "\n"


def _read_block(
    lines: list[str], marker_index: int, fence: str
) -> ModelDiagramBlock | None:
    """The fenced block after a marker, skipping blank lines; ``None`` when there is none."""
    index = marker_index + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not lines[index].startswith(fence):
        return None
    language = lines[index][len(fence) :].strip()
    end = index + 1
    while end < len(lines) and not lines[end].startswith(fence):
        end += 1
    if end >= len(lines):
        return None
    return ModelDiagramBlock(
        language=language,
        body=tuple(lines[index + 1 : end]),
        fence_index=index,
        end_index=end,
    )


def check_diagram_drift(
    request: ModelDiagramDriftCheckInput,
) -> ModelDiagramDriftCheckResult:
    """Judge every diagram of a document against the fragment its marker names."""
    rules = ModelDiagramDriftRules.from_contract(request.contract)
    found: list[ModelValidationIssue] = []

    def add(
        code: str,
        contract_id: str,
        document_line: int,
        diagram_line: int = 0,
        template: str = "",
        **fields: object,
    ) -> None:
        row = rules.row(code)
        if not row.enabled or not row.judges(request.source_name):
            return
        found.append(
            ModelValidationIssue(
                severity=row.severity,
                message=_fill(
                    template or row.message,
                    contract_id=contract_id,
                    **fields,
                ),
                code=code,
                rule_name=code,
                line_number=document_line,
                context={
                    "contract_id": contract_id,
                    "diagram_line": str(diagram_line),
                },
            )
        )

    marker_row = rules.row("malformed_marker")
    diagram_marker = marker_row.pattern("diagram_marker_pattern")
    fragment_marker = marker_row.pattern("fragment_marker_pattern")
    fence = marker_row.texts["fence"]
    lines = request.text.splitlines()

    fragments: dict[str, tuple[int, ModelDiagramBlock]] = {}
    diagrams: list[tuple[str, str, str, bool, int, ModelDiagramBlock]] = []
    for index, raw in enumerate(lines):
        marker = raw.strip()
        fragment_match = fragment_marker.match(marker)
        diagram_match = diagram_marker.match(marker)
        if not fragment_match and not diagram_match:
            continue
        block = _read_block(lines, index, fence)
        if fragment_match:
            contract_id = f"{fragment_match[1]}:{fragment_match[2]}"
            if block is None or block.language != marker_row.texts["yaml_language"]:
                add(
                    "malformed_marker",
                    contract_id,
                    index + 1,
                    problem=marker_row.texts["missing_yaml_message"],
                )
            elif contract_id in fragments:
                add(
                    "duplicate_fragment",
                    contract_id,
                    index + 1,
                    first_line=fragments[contract_id][0],
                )
            else:
                fragments[contract_id] = (index + 1, block)
        elif diagram_match:
            contract_id = f"{diagram_match[1]}:{diagram_match[2]}"
            if block is None or block.language != marker_row.texts["mermaid_language"]:
                add(
                    "malformed_marker",
                    contract_id,
                    index + 1,
                    problem=marker_row.texts["missing_mermaid_message"],
                )
            else:
                diagrams.append(
                    (
                        contract_id,
                        diagram_match[1],
                        diagram_match[2],
                        bool(diagram_match[3]),
                        index + 1,
                        block,
                    )
                )

    loaded: dict[str, ModelDiagramFragment | None] = {}
    for contract_id, (line, block) in fragments.items():
        try:
            loaded[contract_id] = _load_fragment("\n".join(block.body) + "\n")
        except ModelOnexError as refused:
            loaded[contract_id] = None
            add("fragment_refused", contract_id, line, reason=str(refused))

    drawn: set[str] = set()
    differs = rules.row("diagram_differs")
    for contract_id, node, block_name, collapsed, marker_line, block in diagrams:
        drawn.add(contract_id)
        _check_caption(lines, node, contract_id, block, add)
        if contract_id not in fragments:
            add("diagram_without_fragment", contract_id, marker_line)
            continue
        fragment = loaded[contract_id]
        if fragment is None:
            continue
        if fragment.kind != block_name:
            add(
                "fragment_refused",
                contract_id,
                fragments[contract_id][0],
                template=rules.row("fragment_refused").texts["mismatch_message"],
                block=block_name,
                kind=fragment.kind,
            )
            continue
        if fragment.kind == "state_machine" and collapsed:
            add("view_not_supported", contract_id, marker_line)
            continue
        generated = (
            _render_state_machine(differs, fragment)
            if fragment.kind == "state_machine"
            else _render_graph(differs, fragment, collapsed)
        )
        _compare(differs, contract_id, generated, block, add)

    for contract_id, (line, _) in fragments.items():
        if contract_id not in drawn:
            add("fragment_without_diagram", contract_id, line)

    issues = sorted(found, key=lambda issue: issue.line_number or 0)
    return ModelDiagramDriftCheckResult(
        issues=tuple(issues),
        diagrams_checked=len(diagrams),
        fragments_found=len(fragments),
        exit_code=1 if any(i.severity.is_error_or_above() for i in issues) else 0,
    )


def _check_caption(
    lines: list[str],
    node: str,
    contract_id: str,
    block: ModelDiagramBlock,
    add: Callable[..., None],
) -> None:
    index = block.end_index + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or node not in lines[index]:
        add("missing_contract_line", contract_id, block.end_index + 1, node=node)


def _compare(
    row: ModelTaskCriteriaRuleRow,
    contract_id: str,
    generated: str,
    block: ModelDiagramBlock,
    add: Callable[..., None],
) -> None:
    expected = generated.splitlines()
    found = [line.rstrip() for line in block.body]
    for position in range(max(len(expected), len(found))):
        want = expected[position] if position < len(expected) else None
        have = found[position] if position < len(found) else None
        if want == have:
            continue
        number = position + 1
        add(
            "diagram_differs",
            contract_id,
            block.fence_index + 1 + number,
            number,
            line=number,
            want=want.strip() if want is not None else row.texts["no_line_text"],
            have=have.strip() if have is not None else row.texts["no_line_text"],
        )
        return
