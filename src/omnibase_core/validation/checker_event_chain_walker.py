# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure contract event-chain checks: parsed facts in, issues out (OMN-21558).

Topic paths, event alphabet paths, analysis fields and remediation live in the
validation contract's rule parameters. Only armed machines supplied by the
contract walker are analyzed. This module performs no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_fsm_analysis_result import (
    ModelFSMAnalysisResult,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings
from omnibase_core.validation.validator_fsm_analysis import analyze_fsm

__all__ = ["check_event_chain"]


def _paths(rule: ModelValidatorRule, key: str) -> tuple[str, ...]:
    paths = rule_strings(rule, key)
    for path in paths:
        for segment in path.split("."):
            name = segment.removesuffix("[]")
            if not name or "[" in name or "]" in name or ("*" in name and name != "*"):
                raise ModelOnexError(
                    message=f"rule {rule.rule_id!r}: invalid path {path!r}",
                    error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                )
    return paths


def _validate_row(rule: ModelValidatorRule) -> None:
    """Read every parameter of an enabled row before judging any facts."""
    kind = rule_string(rule, "kind")
    rule_string(rule, "remediation")
    if kind == "unconsumed_topic":
        _paths(rule, "producer_paths")
        _paths(rule, "consumer_paths")
        _paths(rule, "external_consumer_paths")
    elif kind == "unproduced_topic":
        _paths(rule, "consumer_paths")
        _paths(rule, "producer_paths")
        _paths(rule, "external_producer_paths")
    elif kind == "fsm_exit":
        for field in rule_strings(rule, "analysis_fields"):
            definition = ModelFSMAnalysisResult.model_fields.get(field)
            if (
                definition is None
                or definition.annotation not in (list[str], list[list[str]])
                or field == "errors"
                or field == "dead_transitions"
            ):
                raise ModelOnexError(
                    message=f"rule {rule.rule_id!r}: unknown analysis_fields entry {field!r}; expected a state-name field",
                    error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                )
    elif kind == "undeclared_trigger":
        _paths(rule, "alphabet_paths")
    else:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: unknown kind {kind!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )


def _values(document: Mapping[str, object], paths: Sequence[str]) -> set[str]:
    """Resolve dotted mapping keys, mapping wildcards and mapping-list steps."""
    found: set[str] = set()
    for path in paths:
        values: list[object] = [document]
        for segment in path.split("."):
            following: list[object] = []
            for value in values:
                if not isinstance(value, Mapping):
                    continue
                name = segment.removesuffix("[]")
                selected = list(value.values()) if name == "*" else [value.get(name)]
                for item in selected:
                    if segment.endswith("[]"):
                        if isinstance(item, list):
                            following.extend(v for v in item if isinstance(v, Mapping))
                    else:
                        following.append(item)
            values = following
        for value in values:
            if isinstance(value, str):
                found.add(value)
            elif isinstance(value, list):
                found.update(item for item in value if isinstance(item, str))
    return found


def _issue(rule: ModelValidatorRule, path: str, detail: str) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        code=rule.rule_id,
        rule_name=rule.rule_id,
        file_path=Path(path),
        message=f"{detail} -- {rule_string(rule, 'remediation')}",
    )


def check_event_chain(
    documents: Mapping[str, Mapping[str, object]],
    fsms: Mapping[str, ModelFSMSubcontract],
    rules: Sequence[ModelValidatorRule],
) -> list[ModelValidationIssue]:
    """Judge the whole corpus, ordered by rule, contract path, then entity name."""
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        _validate_row(rule)
        kind = rule_string(rule, "kind")
        if kind == "unconsumed_topic" or kind == "unproduced_topic":
            source_key = (
                "producer_paths" if kind == "unconsumed_topic" else "consumer_paths"
            )
            peer_key = (
                "consumer_paths" if kind == "unconsumed_topic" else "producer_paths"
            )
            external_key = (
                "external_consumer_paths"
                if kind == "unconsumed_topic"
                else "external_producer_paths"
            )
            peers: set[str] = set()
            for document in documents.values():
                peers.update(_values(document, _paths(rule, peer_key)))
                peers.update(_values(document, _paths(rule, external_key)))
            for path, document in sorted(documents.items()):
                for topic in sorted(
                    _values(document, _paths(rule, source_key)) - peers
                ):
                    issues.append(
                        _issue(rule, path, f"topic {topic!r} has no corpus counterpart")
                    )
        elif kind == "fsm_exit":
            for path, fsm in sorted(fsms.items()):
                analysis = analyze_fsm(fsm).model_dump(mode="json")
                names: set[str] = set()
                for field in rule_strings(rule, "analysis_fields"):
                    for item in analysis[field]:
                        names.add(
                            item if isinstance(item, str) else ", ".join(sorted(item))
                        )
                for name in sorted(names):
                    issues.append(_issue(rule, path, f"state {name!r} has no exit"))
        elif kind == "undeclared_trigger":
            for path, fsm in sorted(fsms.items()):
                alphabet = _values(
                    documents.get(path, {}), _paths(rule, "alphabet_paths")
                )
                for transition in sorted(
                    fsm.transitions, key=lambda t: t.transition_name
                ):
                    if transition.trigger not in alphabet:
                        issues.append(
                            _issue(
                                rule,
                                path,
                                f"transition {transition.transition_name!r} uses undeclared event {transition.trigger!r}",
                            )
                        )
    return issues
