# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure contract-chain coverage: typed facts in, ordered issues and tables out.

Rule identifiers, templates, paths and remediation are supplied by the validation
contract. Generated cases are parity scaffolds, not proof of execution. No I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, cast

from omnibase_core.enums.enum_contract_chain_obligation_kind import (
    EnumContractChainObligationKind,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_contract_chain_binding import (
    ModelContractChainBinding,
)
from omnibase_core.models.validation.model_contract_chain_coverage_row import (
    ModelContractChainCoverageRow,
)
from omnibase_core.models.validation.model_contract_chain_facts import (
    ModelContractChainFacts,
)
from omnibase_core.models.validation.model_contract_chain_generated_case import (
    ModelContractChainGeneratedCase,
)
from omnibase_core.models.validation.model_contract_chain_obligation import (
    ModelContractChainObligation,
)
from omnibase_core.validation.checker_event_chain_walker import (
    _issue,
    _paths,
    check_event_chain,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)
from omnibase_core.validation.validator_fsm_analysis import analyze_fsm


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=f"rule {rule.rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
    )


def _template(rule: ModelValidatorRule, key: str, **values: str) -> str:
    try:
        return rule_string(rule, key).format(**values)
    except (KeyError, ValueError, IndexError, AttributeError) as exc:
        raise _invalid(rule, f"invalid {key}: {exc}") from exc


def _validate_row(rule: ModelValidatorRule) -> None:
    """Validate parameters even when facts are empty; execution evidence stays held."""
    kind = rule_string(rule, "kind")
    rule_string(rule, "remediation")
    if kind == EnumContractChainObligationKind.TRANSITION:
        _template(rule, "id_template", owner="owner", transition_name="transition")
        rule_string(rule, "marker_name")
        rule_string(rule, "overlay_marker_name")
        rule_strings(rule, "test_roots")
        rule_strings(rule, "test_file_globs")
        rule_strings(rule, "test_exclude_patterns")
        rule_string(rule, "generated_cases_glob")
        rule_string(rule, "missing_marker")
        rule_strings(rule, "overlay_profiles")
        scenario_kind = rule_string(rule, "scenario_kind")
        if scenario_kind != "stub_rows" and scenario_kind != "node_operation":
            raise _invalid(rule, f"invalid scenario_kind {scenario_kind!r}")
        _template(rule, "scenario_node_template", owner="owner", kind=kind, id="id")
        _template(
            rule, "scenario_operation_template", owner="owner", kind=kind, id="id"
        )
        rule_strings(rule, "allowed_differences")
    elif kind == EnumContractChainObligationKind.GRAPH_EDGE:
        rule_string(rule, "nodes_path")
        rule_string(rule, "node_id_key")
        rule_string(rule, "dependencies_key")
        _template(rule, "id_template", owner="owner", from_node="from", to_node="to")
    elif kind == EnumContractChainObligationKind.GUARD_BRANCH:
        if len(set(rule_strings(rule, "branches"))) != 2:
            raise _invalid(rule, "branches must name two distinct guard outcomes")
        _template(
            rule,
            "id_template",
            owner="owner",
            transition_name="transition",
            branch="branch",
        )
    elif kind == EnumContractChainObligationKind.LOOP_EXIT:
        rule_string(rule, "nodes_path")
        rule_string(rule, "node_id_key")
        rule_string(rule, "loops_to_path")
        _template(rule, "id_template", owner="owner", node_id="node")
        _template(rule, "fsm_id_template", owner="owner", transition_name="transition")
    elif kind == "unconsumed_topic" or kind == "unproduced_topic":
        _paths(rule, "producer_paths")
        _paths(rule, "consumer_paths")
        _paths(
            rule,
            "external_consumer_paths"
            if kind == "unconsumed_topic"
            else "external_producer_paths",
        )
    elif kind == "dead" or kind == "failure_exit":
        rule_string(rule, "wildcard_state")
    elif kind == "execution_evidence":
        rule_string(rule, "evidence_glob")
        if rule_int(rule, "minimum_executions") < 1:
            raise _invalid(rule, "minimum_executions must be positive")
    elif kind != "unreachable":
        raise _invalid(rule, f"unknown kind {kind!r}")


def validate_rules(rules: Sequence[ModelValidatorRule]) -> None:
    """Validate all rows before deriving or judging facts, including held evidence."""
    for rule in rules:
        _validate_row(rule)


def coverage_settings(rules: Sequence[ModelValidatorRule]) -> ModelValidatorRule:
    """The transition row owns common binding, table and generation parameters."""
    for rule in rules:
        if rule_string(rule, "kind") == EnumContractChainObligationKind.TRANSITION:
            return rule
    raise ModelOnexError(
        message="coverage rules need a transition row for binding parameters",
        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
    )


def _at(document: Mapping[str, object], path: str) -> object:
    value: object = document
    for segment in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(segment)
    return value


def _nodes(
    document: Mapping[str, object], rule: ModelValidatorRule
) -> list[Mapping[str, object]]:
    value = _at(document, rule_string(rule, "nodes_path"))
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def derive_obligations(
    facts: ModelContractChainFacts, rules: Sequence[ModelValidatorRule]
) -> tuple[ModelContractChainObligation, ...]:
    """Derive every structural obligation, including unreachable transitions."""
    validate_rules(rules)
    obligations: dict[str, ModelContractChainObligation] = {}

    def add(owner: str, kind: EnumContractChainObligationKind, identity: str) -> None:
        if identity in obligations:
            raise ModelOnexError(
                message=f"duplicate obligation id {identity!r}; check id templates and entity names",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
        obligations[identity] = ModelContractChainObligation(
            owner=owner, kind=kind, id=identity
        )

    for rule in rules:
        kind = rule_string(rule, "kind")
        if (
            kind == EnumContractChainObligationKind.TRANSITION
            or kind == EnumContractChainObligationKind.GUARD_BRANCH
        ):
            for owner, fsm in sorted(facts.fsms.items()):
                for transition in fsm.transitions:
                    if kind == EnumContractChainObligationKind.TRANSITION:
                        add(
                            owner,
                            EnumContractChainObligationKind.TRANSITION,
                            _template(
                                rule,
                                "id_template",
                                owner=owner,
                                transition_name=transition.transition_name,
                            ),
                        )
                    elif transition.conditions:
                        for branch in rule_strings(rule, "branches"):
                            add(
                                owner,
                                EnumContractChainObligationKind.GUARD_BRANCH,
                                _template(
                                    rule,
                                    "id_template",
                                    owner=owner,
                                    transition_name=transition.transition_name,
                                    branch=branch,
                                ),
                            )
        elif kind == EnumContractChainObligationKind.GRAPH_EDGE:
            for owner, document in sorted(facts.documents.items()):
                for node in _nodes(document, rule):
                    target = node.get(rule_string(rule, "node_id_key"))
                    dependencies = node.get(rule_string(rule, "dependencies_key"), [])
                    if isinstance(target, str) and isinstance(dependencies, list):
                        for source in dependencies:
                            if isinstance(source, str):
                                add(
                                    owner,
                                    EnumContractChainObligationKind.GRAPH_EDGE,
                                    _template(
                                        rule,
                                        "id_template",
                                        owner=owner,
                                        from_node=source,
                                        to_node=target,
                                    ),
                                )
        elif kind == EnumContractChainObligationKind.LOOP_EXIT:
            for owner, document in sorted(facts.documents.items()):
                for node in _nodes(document, rule):
                    name = node.get(rule_string(rule, "node_id_key"))
                    if isinstance(name, str) and _at(
                        node, rule_string(rule, "loops_to_path")
                    ):
                        add(
                            owner,
                            EnumContractChainObligationKind.LOOP_EXIT,
                            _template(rule, "id_template", owner=owner, node_id=name),
                        )
            for owner, fsm in sorted(facts.fsms.items()):
                for transition in fsm.transitions:
                    if transition.from_state == transition.to_state and any(
                        other.from_state == transition.from_state
                        and other.transition_name != transition.transition_name
                        for other in fsm.transitions
                    ):
                        add(
                            owner,
                            EnumContractChainObligationKind.LOOP_EXIT,
                            _template(
                                rule,
                                "fsm_id_template",
                                owner=owner,
                                transition_name=transition.transition_name,
                            ),
                        )
    return tuple(
        sorted(obligations.values(), key=lambda o: (o.owner, o.kind.value, o.id))
    )


def _toward(fsm: ModelFSMSubcontract, targets: set[str], wildcard: str) -> set[str]:
    """Reverse graph traversal, expanding wildcard source transitions."""
    names = {state.state_name for state in fsm.states}
    incoming: dict[str, set[str]] = {}
    for transition in fsm.transitions:
        sources = (
            names if transition.from_state == wildcard else {transition.from_state}
        )
        incoming.setdefault(transition.to_state, set()).update(sources)
    reached = set(targets)
    pending = list(targets)
    while pending:
        for source in incoming.get(pending.pop(), set()) - reached:
            reached.add(source)
            pending.append(source)
    return reached


def check_contract_chain_coverage(
    facts: ModelContractChainFacts, rules: Sequence[ModelValidatorRule]
) -> list[ModelValidationIssue]:
    """Judge rules in contract order, then owner and entity name."""
    obligations = derive_obligations(facts, rules)
    bound = {binding.obligation_ref for binding in facts.bindings}
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        kind = rule_string(rule, "kind")
        if kind in EnumContractChainObligationKind:
            for obligation in obligations:
                if obligation.kind.value == kind and obligation.id not in bound:
                    issues.append(
                        _issue(
                            rule,
                            obligation.owner,
                            f"obligation {obligation.id!r} has no binding",
                        )
                    )
        elif kind == "unconsumed_topic" or kind == "unproduced_topic":
            issues.extend(check_event_chain(facts.documents, facts.fsms, [rule]))
        elif kind == "unreachable" or kind == "dead" or kind == "failure_exit":
            for owner, fsm in sorted(facts.fsms.items()):
                analysis = analyze_fsm(fsm)
                unreachable = set(analysis.unreachable_states)
                if kind == "unreachable":
                    names = unreachable
                else:
                    terminal = set(fsm.terminal_states)
                    reachable = {state.state_name for state in fsm.states} - unreachable
                    wildcard = rule_string(rule, "wildcard_state")
                    can_finish = _toward(fsm, terminal, wildcard)
                    # SCC results cover closed cycles; reverse reachability also
                    # catches predecessors, sinks, and cycles with only dead exits.
                    cycles = {
                        state
                        for cycle in analysis.cycles_without_exit
                        for state in cycle
                    }
                    dead = (
                        ((reachable - can_finish) | (cycles - can_finish))
                        - terminal
                        - unreachable
                    )
                    if kind == "dead":
                        names = dead
                    else:
                        errors = set(fsm.error_states)
                        can_succeed = _toward(fsm, terminal - errors, wildcard)
                        can_fail = _toward(fsm, errors, wildcard)
                        names = (reachable & can_succeed) - can_fail - dead - terminal
                for name in sorted(names):
                    issues.append(
                        _issue(rule, owner, f"state {name!r} violates {rule.rule_id}")
                    )
        # Execution evidence is deliberately held, even if its row is toggled.
    return issues


def build_coverage_table(
    facts: ModelContractChainFacts, rules: Sequence[ModelValidatorRule]
) -> tuple[ModelContractChainCoverageRow, ...]:
    """One deterministic row per obligation, with the first binding by file/line."""
    obligations = derive_obligations(facts, rules)
    missing = rule_string(coverage_settings(rules), "missing_marker")
    bindings: dict[str, list[ModelContractChainBinding]] = {}
    for binding in sorted(facts.bindings, key=lambda b: (b.file, b.line, b.overlays)):
        bindings.setdefault(binding.obligation_ref, []).append(binding)
    rows = []
    for obligation in obligations:
        matches = bindings.get(obligation.id, [])
        rows.append(
            ModelContractChainCoverageRow(
                owner=obligation.owner,
                kind=obligation.kind,
                id=obligation.id,
                location=f"{matches[0].file}:{matches[0].line}" if matches else missing,
                overlays=tuple(
                    sorted({overlay for match in matches for overlay in match.overlays})
                ),
            )
        )
    return tuple(rows)


def render_coverage_table(rows: Sequence[ModelContractChainCoverageRow]) -> str:
    """Render a stable Markdown table, escaping cell separators and newlines."""

    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = [
        "| Owner | Kind | ID | Location | Overlays |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda r: (r.owner, r.kind.value, r.id)):
        lines.append(
            "| "
            + " | ".join(
                cell(value)
                for value in (
                    row.owner,
                    row.kind.value,
                    row.id,
                    row.location,
                    ", ".join(row.overlays),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def generate_cases(
    rows: Sequence[ModelContractChainCoverageRow], rules: Sequence[ModelValidatorRule]
) -> tuple[ModelContractChainGeneratedCase, ...]:
    """Scaffold one missing obligation over the contract's overlay profiles."""
    validate_rules(rules)
    settings = coverage_settings(rules)
    return tuple(
        ModelContractChainGeneratedCase(
            kind=cast(
                Literal["stub_rows", "node_operation"],
                rule_string(settings, "scenario_kind"),
            ),
            node=_template(
                settings,
                "scenario_node_template",
                owner=row.owner,
                kind=row.kind.value,
                id=row.id,
            ),
            operation=_template(
                settings,
                "scenario_operation_template",
                owner=row.owner,
                kind=row.kind.value,
                id=row.id,
            ),
            fixture={"obligation_ref": row.id},
            allowed_differences=rule_strings(settings, "allowed_differences"),
            obligation_ref=row.id,
            overlays=rule_strings(settings, "overlay_profiles"),
        )
        for row in sorted(rows, key=lambda r: (r.owner, r.kind.value, r.id))
        if row.location == rule_string(settings, "missing_marker")
    )
