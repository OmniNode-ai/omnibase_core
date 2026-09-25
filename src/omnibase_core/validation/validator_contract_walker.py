# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract walker, report-only (OMN-19553).

Golden-chain validation layer plan r4, Phase 3 (walker MVP). The walker reads
node ``contract.yaml`` files, composes each orchestrator's typed state machine
with the reducer machines its contract links to, walks the reachable product
graph and reports, per workflow:

* golden paths (initial state to each non-error terminal) and error paths,
  selected by an all-edges cover with loop bound 1, with the realized path
  count reported next to the edge count and the cyclomatic number;
* error edges: declared transitions into a declared error state that fire;
* illegal (state, trigger) pairs: a trigger in a component's declared alphabet
  with no declared transition out of a reached, non-terminal state, i.e. an
  event the component must reject there;
* unreachable states, dead states (reached, no path to a terminal) and
  uncovered transitions (declared, never fired by a reachable edge).

It generates no tests; that is a later plan step. It fails nothing: the CLI
exits 0 whatever it finds (report-only by the operator ruling of 2026-09-25).

Loading is strict. A machine is walkable only when its ``state_machine:`` block
declares ``state_machine_version``, carries no key the typed FSM models do not
declare (they are ``extra="ignore"``, so a misspelt key would otherwise load and
vanish), and loads through ``ModelFSMSubcontract``. Every other machine-declaring
contract, including the untyped ``fsm:`` dialect, is reported NOT_ARMED with the
reason and stays in the counts.

Composition. The workflow owner is an orchestrator, or a reducer no
orchestrator links. A reducer is linked to an orchestrator by contract-declared
evidence only: a topic one publishes and the other subscribes to
(``event_bus``), or the reducer's node package named in a module path in the
orchestrator's contract. Components synchronise on trigger names they share
and interleave on the rest. Triggers are untyped symbols today (plan r4 Phase -1
deliverable 4), so this is name-level synchronisation, and the report says which
triggers it synchronised on.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from itertools import product as cartesian_product
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_contract_walk import (
    EnumContractWalkLinkEvidence,
    EnumContractWalkPathKind,
    EnumContractWalkRole,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.fsm.model_fsm_operation import ModelFSMOperation
from omnibase_core.models.fsm.model_fsm_transition_action import (
    ModelFSMTransitionAction,
)
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_contract_walk_component import (
    ModelContractWalkComponent,
)
from omnibase_core.models.validation.model_contract_walk_illegal_pair import (
    ModelContractWalkIllegalPair,
)
from omnibase_core.models.validation.model_contract_walk_machine import (
    ModelContractWalkMachine,
)
from omnibase_core.models.validation.model_contract_walk_not_armed import (
    ModelContractWalkNotArmed,
)
from omnibase_core.models.validation.model_contract_walk_path import (
    ModelContractWalkPath,
)
from omnibase_core.models.validation.model_contract_walk_report import (
    ModelContractWalkReport,
)
from omnibase_core.models.validation.model_contract_walk_state_ref import (
    ModelContractWalkStateRef,
)
from omnibase_core.models.validation.model_contract_walk_step import (
    ModelContractWalkStep,
)
from omnibase_core.models.validation.model_contract_walk_summary import (
    ModelContractWalkSummary,
)
from omnibase_core.models.validation.model_contract_walk_transition_ref import (
    ModelContractWalkTransitionRef,
)
from omnibase_core.models.validation.model_contract_walk_workflow import (
    ModelContractWalkWorkflow,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_fsm_analysis import analyze_fsm

__all__ = [
    "DEFAULT_MAX_PRODUCT_STATES",
    "find_unknown_fsm_keys",
    "main",
    "walk_contracts",
]

# A product graph larger than this is reported truncated rather than walked
# further; the cap is in the report, never silent.
DEFAULT_MAX_PRODUCT_STATES = 20000

_WILDCARD = "*"

# A contract whose YAML does not load still counts as NOT_ARMED when its text
# declares a machine at top level; it never drops out of the denominator.
_DECLARES_MACHINE = re.compile(r"^(state_machine|fsm):", re.MULTILINE)

ProductState = tuple[str, ...]
ProductEdge = tuple[ProductState, str, ProductState, tuple[tuple[int, int], ...]]


# ---------------------------------------------------------------------------
# Strict loading
# ---------------------------------------------------------------------------


def _declared_keys(model: type[BaseModel]) -> frozenset[str]:
    return frozenset(name for name in model.model_fields if not name.isupper())


def find_unknown_fsm_keys(block: object) -> list[str]:
    """Return every key of a raw ``state_machine`` mapping the typed models do not declare.

    The FSM model family ignores unknown keys, so a misspelt key loads clean
    and disappears. This check is the strict path in front of the walker.
    """
    found: list[str] = []

    def check(
        raw: object,
        model: type[BaseModel],
        where: str,
        nested: Mapping[str, tuple[type[BaseModel], bool]],
    ) -> None:
        if not isinstance(raw, dict):
            found.append(f"{where}: expected a mapping, got {type(raw).__name__}")
            return
        allowed = _declared_keys(model)
        for key, value in raw.items():
            if key not in allowed:
                found.append(f"{where}.{key}")
                continue
            if key in nested:
                child, is_list = nested[key]
                if is_list and isinstance(value, list):
                    for index, item in enumerate(value):
                        check(item, child, f"{where}.{key}[{index}]", {})
                elif not is_list:
                    check(value, child, f"{where}.{key}", {})

    if not isinstance(block, dict):
        return ["state_machine: expected a mapping"]
    check(
        block,
        ModelFSMSubcontract,
        "state_machine",
        {
            "version": (ModelSemVer, False),
            "state_machine_version": (ModelSemVer, False),
            "operations": (ModelFSMOperation, True),
        },
    )
    for index, state in enumerate(block.get("states") or []):
        check(
            state,
            ModelFSMStateDefinition,
            f"state_machine.states[{index}]",
            {"version": (ModelSemVer, False)},
        )
    for index, transition in enumerate(block.get("transitions") or []):
        check(
            transition,
            ModelFSMStateTransition,
            f"state_machine.transitions[{index}]",
            {
                "version": (ModelSemVer, False),
                "conditions": (ModelFSMTransitionCondition, True),
                "actions": (ModelFSMTransitionAction, True),
            },
        )
    return found


def _role(node_type: object) -> EnumContractWalkRole:
    text = str(node_type or "").lower()
    if "orchestrator" in text:
        return EnumContractWalkRole.ORCHESTRATOR
    if "reducer" in text:
        return EnumContractWalkRole.REDUCER
    return EnumContractWalkRole.OTHER


def _topics(event_bus: object, key: str) -> frozenset[str]:
    if not isinstance(event_bus, dict):
        return frozenset()
    found: set[str] = set()
    for entry in event_bus.get(key) or []:
        if isinstance(entry, str):
            found.add(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("topic"), str):
            found.add(entry["topic"])
    return frozenset(found)


def _all_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)


def _load(
    roots: Sequence[Path],
) -> tuple[int, list[ModelContractWalkMachine], list[ModelContractWalkNotArmed]]:
    """Read every contract.yaml under ``roots``; return (scanned, walkable, NOT_ARMED)."""
    scanned = 0
    machines: list[ModelContractWalkMachine] = []
    not_armed_list: list[ModelContractWalkNotArmed] = []
    paths: list[tuple[Path, Path]] = []
    for root in roots:
        candidates = [root] if root.is_file() else sorted(root.rglob("contract.yaml"))
        paths.extend((root, path) for path in candidates)
    for root, path in paths:
        scanned += 1
        text = path.read_text(encoding="utf-8")
        try:
            data: object = load_yaml_mapping_no_duplicates(
                text, source=_relative(root, path)
            )
        except (yaml.YAMLError, ValueError) as exc:
            if not _DECLARES_MACHINE.search(text):
                continue
            not_armed_list.append(
                ModelContractWalkNotArmed(
                    node=path.parent.name,
                    contract_path=_relative(root, path),
                    reason=f"contract.yaml does not load: {type(exc).__name__}: {exc}",
                )
            )
            continue
        if not isinstance(data, dict):
            continue
        block = data.get("state_machine")
        has_fsm_dialect = isinstance(data.get("fsm"), dict)
        if not isinstance(block, dict) and not has_fsm_dialect:
            continue
        node = path.parent.name
        rel = _relative(root, path)

        def not_armed(reason: str, node: str = node, rel: str = rel) -> None:
            not_armed_list.append(
                ModelContractWalkNotArmed(node=node, contract_path=rel, reason=reason)
            )

        if not isinstance(block, dict):
            not_armed("declares the untyped fsm: dialect, not a typed state_machine")
            continue
        if "state_machine_version" not in block:
            not_armed("state_machine block declares no state_machine_version")
            continue
        unknown = find_unknown_fsm_keys(block)
        if unknown:
            not_armed(f"keys the typed FSM models do not declare: {', '.join(unknown)}")
            continue
        try:
            fsm = ModelFSMSubcontract.model_validate(block)
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(part) for part in first.get("loc", ()))
            not_armed(
                f"does not load into ModelFSMSubcontract: {where}: {first['msg']}"
            )
            continue
        event_bus = data.get("event_bus")
        machines.append(
            ModelContractWalkMachine(
                node=node,
                contract_path=rel,
                role=_role(data.get("node_type")),
                fsm=fsm,
                publishes=_topics(event_bus, "publish_topics"),
                subscribes=_topics(event_bus, "subscribe_topics"),
                strings=tuple(_all_strings(data)),
            )
        )
    return scanned, machines, not_armed_list


def _relative(root: Path, path: Path) -> str:
    base = root if root.is_dir() else root.parent
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------


def _link(
    owner: ModelContractWalkMachine, reducer: ModelContractWalkMachine
) -> tuple[tuple[EnumContractWalkLinkEvidence, ...], tuple[str, ...]]:
    evidence: list[EnumContractWalkLinkEvidence] = []
    detail: list[str] = []
    shared = sorted(
        (owner.publishes & reducer.subscribes) | (reducer.publishes & owner.subscribes)
    )
    if shared:
        evidence.append(EnumContractWalkLinkEvidence.TOPIC)
        detail.extend(shared)
    needle = f".{reducer.node}."
    tail = f".{reducer.node}"
    refs = sorted({s for s in owner.strings if needle in s or s.endswith(tail)})
    if refs:
        evidence.append(EnumContractWalkLinkEvidence.MODULE_REFERENCE)
        detail.extend(refs)
    return tuple(evidence), tuple(detail)


# ---------------------------------------------------------------------------
# Product graph
# ---------------------------------------------------------------------------


def _moves(
    fsm: ModelFSMSubcontract,
) -> dict[tuple[str, str], list[tuple[int, str]]]:
    """Map (state, trigger) to the declared transitions it may fire, wildcards expanded."""
    terminal = set(fsm.terminal_states)
    names = [state.state_name for state in fsm.states]
    moves: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for index, transition in enumerate(fsm.transitions):
        sources = (
            [name for name in names if name not in terminal]
            if transition.from_state == _WILDCARD
            else [transition.from_state]
        )
        for source in sources:
            moves.setdefault((source, transition.trigger), []).append(
                (index, transition.to_state)
            )
    return moves


ProductGraph = tuple[list[ProductState], list[ProductEdge], bool]


def _build_product(
    machines: Sequence[ModelContractWalkMachine], max_states: int
) -> ProductGraph:
    """Reachable synchronous product: (states in BFS order, edges, truncated)."""
    alphabets = [
        sorted({transition.trigger for transition in m.fsm.transitions})
        for m in machines
    ]
    triggers = sorted({t for alphabet in alphabets for t in alphabet})
    participants = {
        t: [i for i, alphabet in enumerate(alphabets) if t in alphabet]
        for t in triggers
    }
    moves = [_moves(m.fsm) for m in machines]
    initial: ProductState = tuple(m.fsm.initial_state for m in machines)
    seen = {initial}
    order = [initial]
    queue: deque[ProductState] = deque([initial])
    edges: list[ProductEdge] = []
    truncated = False
    while queue:
        state = queue.popleft()
        for trigger in triggers:
            choices: list[list[tuple[int, int, str]]] = []
            for i in participants[trigger]:
                options = moves[i].get((state[i], trigger), [])
                if not options:
                    choices = []
                    break
                choices.append([(i, index, target) for index, target in options])
            if not choices:
                continue
            for combo in cartesian_product(*choices):
                target = list(state)
                fired: list[tuple[int, int]] = []
                for i, index, to_state in combo:
                    target[i] = to_state
                    fired.append((i, index))
                nxt = tuple(target)
                edges.append((state, trigger, nxt, tuple(fired)))
                if nxt not in seen:
                    if len(seen) >= max_states:
                        truncated = True
                        continue
                    seen.add(nxt)
                    order.append(nxt)
                    queue.append(nxt)
    return order, edges, truncated


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------


def _shortest_prefixes(
    initial: ProductState, edges: Sequence[ProductEdge]
) -> dict[ProductState, int | None]:
    """BFS tree from the initial state: each reached state maps to its tree edge index."""
    outgoing: dict[ProductState, list[int]] = {}
    for i, edge in enumerate(edges):
        outgoing.setdefault(edge[0], []).append(i)
    parent: dict[ProductState, int | None] = {initial: None}
    queue: deque[ProductState] = deque([initial])
    while queue:
        state = queue.popleft()
        for i in outgoing.get(state, []):
            target = edges[i][2]
            if target not in parent:
                parent[target] = i
                queue.append(target)
    return parent


def _prefix(
    edges: Sequence[ProductEdge],
    parent: Mapping[ProductState, int | None],
    state: ProductState,
) -> list[int]:
    path: list[int] = []
    index = parent.get(state)
    while index is not None:
        path.append(index)
        index = parent[edges[index][0]]
    path.reverse()
    return path


def _toward_terminal(
    edges: Sequence[ProductEdge], terminals: set[ProductState]
) -> dict[ProductState, int | None]:
    """For each state that can reach a terminal, the first edge of a shortest way there."""
    incoming: dict[ProductState, list[int]] = {}
    for i, edge in enumerate(edges):
        incoming.setdefault(edge[2], []).append(i)
    step: dict[ProductState, int | None] = dict.fromkeys(sorted(terminals))
    queue: deque[ProductState] = deque(sorted(terminals))
    while queue:
        state = queue.popleft()
        for i in incoming.get(state, []):
            source = edges[i][0]
            if source not in step:
                step[source] = i
                queue.append(source)
    return step


def _suffix(
    edges: Sequence[ProductEdge],
    step: Mapping[ProductState, int | None],
    state: ProductState,
) -> list[int]:
    path: list[int] = []
    index = step.get(state)
    while index is not None:
        path.append(index)
        index = step.get(edges[index][2])
    return path


def _cover(
    initial: ProductState,
    edges: Sequence[ProductEdge],
    terminals: set[ProductState],
) -> list[list[int]]:
    """All-edges cover, loop bound 1: every reachable edge lies on a selected path.

    One shortest path to each reachable terminal first, then, for each edge in
    declaration order not yet covered, the shortest prefix to its source, the
    edge, and the shortest way on to a terminal (or nothing, when no terminal
    is reachable from its target).
    """
    parent = _shortest_prefixes(initial, edges)
    step = _toward_terminal(edges, terminals)
    paths: list[list[int]] = []
    covered: set[int] = set()
    for terminal in sorted(t for t in terminals if t in parent):
        path = _prefix(edges, parent, terminal)
        if path:
            paths.append(path)
            covered.update(path)
    for i, edge in enumerate(edges):
        if i in covered or edge[0] not in parent:
            continue
        path = [*_prefix(edges, parent, edge[0]), i, *_suffix(edges, step, edge[2])]
        paths.append(path)
        covered.update(path)
    return paths


# ---------------------------------------------------------------------------
# Workflow walk
# ---------------------------------------------------------------------------


def _ref(
    machine: ModelContractWalkMachine, index: int
) -> ModelContractWalkTransitionRef:
    transition = machine.fsm.transitions[index]
    return ModelContractWalkTransitionRef(
        node=machine.node,
        transition_name=transition.transition_name,
        from_state=transition.from_state,
        trigger=transition.trigger,
        to_state=transition.to_state,
    )


def _walk_workflow(
    machines: Sequence[ModelContractWalkMachine],
    links: Sequence[tuple[tuple[EnumContractWalkLinkEvidence, ...], tuple[str, ...]]],
    max_states: int,
) -> ModelContractWalkWorkflow:
    owner = machines[0]
    states, edges, truncated = _build_product(machines, max_states)
    reached = set(states)
    owner_terminal = set(owner.fsm.terminal_states)
    owner_error = set(owner.fsm.error_states)
    terminals = {s for s in states if s[0] in owner_terminal}
    initial = states[0]

    paths = _cover(initial, edges, terminals)
    walked: list[ModelContractWalkPath] = []
    for path in paths:
        end = edges[path[-1]][2]
        if end[0] in owner_error:
            kind = EnumContractWalkPathKind.ERROR
        elif end in terminals:
            kind = EnumContractWalkPathKind.GOLDEN
        else:
            kind = EnumContractWalkPathKind.OPEN
        walked.append(
            ModelContractWalkPath(
                kind=kind,
                steps=tuple(
                    ModelContractWalkStep(from_state=a, trigger=t, to_state=b)
                    for a, t, b, _ in (edges[i] for i in path)
                ),
                end_state=end,
            )
        )

    fired: set[tuple[int, int]] = set()
    for _, _, _, pairs in edges:
        fired.update(pairs)

    error_edges: list[ModelContractWalkTransitionRef] = []
    uncovered: list[ModelContractWalkTransitionRef] = []
    unreachable: list[ModelContractWalkStateRef] = []
    illegal: list[ModelContractWalkIllegalPair] = []
    for i, machine in enumerate(machines):
        errors = set(machine.fsm.error_states)
        for index, transition in enumerate(machine.fsm.transitions):
            if (i, index) not in fired:
                uncovered.append(_ref(machine, index))
            elif transition.to_state in errors:
                error_edges.append(_ref(machine, index))
        held = {s[i] for s in reached}
        unreachable.extend(
            ModelContractWalkStateRef(node=machine.node, state=state.state_name)
            for state in machine.fsm.states
            if state.state_name not in held
        )
        moves = _moves(machine.fsm)
        alphabet = sorted({t.trigger for t in machine.fsm.transitions})
        terminal = set(machine.fsm.terminal_states)
        illegal.extend(
            ModelContractWalkIllegalPair(
                node=machine.node, state=state, trigger=trigger
            )
            for state in sorted(held - terminal)
            for trigger in alphabet
            if (state, trigger) not in moves
        )

    dead: list[ProductState] = []
    no_golden_exit: list[ProductState] = []
    if owner_terminal:
        can_finish = set(_toward_terminal(edges, terminals))
        dead = [s for s in states if s not in can_finish]
        golden = {s for s in terminals if s[0] not in owner_error}
        can_succeed = set(_toward_terminal(edges, golden))
        no_golden_exit = [
            s
            for s in states
            if s in can_finish and s not in can_succeed and s[0] not in owner_terminal
        ]

    components = [
        ModelContractWalkComponent(
            node=machine.node,
            contract_path=machine.contract_path,
            role=machine.role,
            link_evidence=link[0],
            link_detail=link[1],
            state_count=len(machine.fsm.states),
            transition_count=len(machine.fsm.transitions),
            perpetual=not machine.fsm.terminal_states,
            analyze_fsm_errors=tuple(analyze_fsm(machine.fsm).errors),
        )
        for machine, link in zip(machines, links, strict=True)
    ]
    alphabets = [{t.trigger for t in m.fsm.transitions} for m in machines]
    sync = sorted(
        {t for t in set().union(*alphabets) if sum(t in a for a in alphabets) > 1}
    )
    edge_count = len(edges)
    return ModelContractWalkWorkflow(
        workflow_owner=owner.node,
        components=tuple(components),
        sync_triggers=tuple(sync),
        product_state_count=len(states),
        product_edge_count=edge_count,
        cyclomatic_bound=max(edge_count - len(states) + 1, 0),
        truncated=truncated,
        selected_path_count=len(walked),
        paths=tuple(walked),
        error_edges=tuple(error_edges),
        illegal_pairs=tuple(illegal),
        unreachable_states=tuple(unreachable),
        dead_states=tuple(dead),
        no_golden_exit_states=tuple(no_golden_exit),
        uncovered_transitions=tuple(uncovered),
    )


def walk_contracts(
    roots: Sequence[Path], *, max_product_states: int = DEFAULT_MAX_PRODUCT_STATES
) -> ModelContractWalkReport:
    """Walk every machine-declaring contract under ``roots`` and return the report."""
    scanned, loaded, not_armed = _load(roots)
    machines = sorted(loaded, key=lambda m: (m.node, m.contract_path))
    orchestrators = [m for m in machines if m.role is EnumContractWalkRole.ORCHESTRATOR]
    others = [m for m in machines if m.role is not EnumContractWalkRole.ORCHESTRATOR]

    workflows: list[ModelContractWalkWorkflow] = []
    linked: set[str] = set()
    for owner in orchestrators:
        members = [owner]
        links: list[
            tuple[tuple[EnumContractWalkLinkEvidence, ...], tuple[str, ...]]
        ] = [((), ())]
        for candidate in others:
            if candidate.role is not EnumContractWalkRole.REDUCER:
                continue
            link = _link(owner, candidate)
            if link[0]:
                members.append(candidate)
                links.append(link)
                linked.add(candidate.contract_path)
        workflows.append(_walk_workflow(members, links, max_product_states))
    for machine in others:
        if machine.contract_path not in linked:
            workflows.append(_walk_workflow([machine], [((), ())], max_product_states))
    workflows.sort(key=lambda w: w.workflow_owner)

    paths = [p for w in workflows for p in w.paths]
    summary = ModelContractWalkSummary(
        contracts_scanned=scanned,
        machine_contracts=len(machines) + len(not_armed),
        walked_contracts=len(machines),
        not_armed_contracts=len(not_armed),
        workflows=len(workflows),
        selected_paths=len(paths),
        golden_paths=sum(p.kind is EnumContractWalkPathKind.GOLDEN for p in paths),
        error_paths=sum(p.kind is EnumContractWalkPathKind.ERROR for p in paths),
        open_paths=sum(p.kind is EnumContractWalkPathKind.OPEN for p in paths),
        error_edges=sum(len(w.error_edges) for w in workflows),
        illegal_pairs=sum(len(w.illegal_pairs) for w in workflows),
        unreachable_states=sum(len(w.unreachable_states) for w in workflows),
        dead_states=sum(len(w.dead_states) for w in workflows),
        no_golden_exit_states=sum(len(w.no_golden_exit_states) for w in workflows),
        uncovered_transitions=sum(len(w.uncovered_transitions) for w in workflows),
        truncated_workflows=sum(w.truncated for w in workflows),
    )
    return ModelContractWalkReport(
        roots=tuple(str(root) for root in roots),
        summary=summary,
        not_armed=tuple(sorted(not_armed, key=lambda n: n.contract_path)),
        workflows=tuple(workflows),
    )


# ---------------------------------------------------------------------------
# CLI (report-only)
# ---------------------------------------------------------------------------


def _summary_lines(report: ModelContractWalkReport) -> list[str]:
    s = report.summary
    lines = [
        "contract walker (report-only; findings never fail this command)",
        f"  contracts scanned {s.contracts_scanned}; declaring a machine "
        f"{s.machine_contracts}; walked {s.walked_contracts}; NOT_ARMED "
        f"{s.not_armed_contracts}",
        f"  workflows {s.workflows}; selected paths {s.selected_paths} "
        f"(golden {s.golden_paths}, error {s.error_paths}, open {s.open_paths}); "
        f"cover all-edges, loop bound 1",
        f"  error edges {s.error_edges}; illegal (state, trigger) pairs "
        f"{s.illegal_pairs}",
        f"  defects: unreachable states {s.unreachable_states}; dead states "
        f"{s.dead_states}; no golden exit {s.no_golden_exit_states}; uncovered "
        f"transitions {s.uncovered_transitions}; "
        f"truncated workflows {s.truncated_workflows}",
    ]
    for workflow in report.workflows:
        nodes = "+".join(c.node for c in workflow.components)
        lines.append(
            f"  {workflow.workflow_owner}: [{nodes}] states {workflow.product_state_count}, "
            f"edges {workflow.product_edge_count}, paths {workflow.selected_path_count}, "
            f"error edges {len(workflow.error_edges)}, unreachable "
            f"{len(workflow.unreachable_states)}, dead {len(workflow.dead_states)}, "
            f"no golden exit {len(workflow.no_golden_exit_states)}, "
            f"uncovered {len(workflow.uncovered_transitions)}"
        )
    for item in report.not_armed:
        lines.append(f"  NOT_ARMED {item.node}: {item.reason}")
    return lines


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m omnibase_core.validation.validator_contract_walker",
        description=(
            "Walk contract state machines and report golden paths, error edges, "
            "illegal state/trigger pairs and defects. Report-only: exits 0 "
            "whatever it finds."
        ),
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=["src"],
        help="Directories (or contract.yaml files) to scan; default src",
    )
    parser.add_argument("--json-out", help="Write the JSON report to this path")
    parser.add_argument(
        "--max-product-states",
        type=int,
        default=DEFAULT_MAX_PRODUCT_STATES,
        help="Product-graph state cap per workflow; hitting it is reported",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = walk_contracts(
        [Path(root) for root in args.roots],
        max_product_states=args.max_product_states,
    )
    if args.json_out:
        text = report.model_dump_json(indent=2) + "\n"
        if args.json_out == "-":
            sys.stdout.write(text)
        else:
            Path(args.json_out).write_text(text, encoding="utf-8")
    sys.stdout.write("\n".join(_summary_lines(report)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
