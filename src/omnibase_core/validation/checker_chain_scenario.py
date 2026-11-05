# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure chain scenario checks: parsed facts in, issues out (OMN-22478).

A node's typed ``chain_scenarios`` block is the source its golden and error chain
tests are generated from. This checker refuses a block that cannot yield a test that
can fail: a missing golden or error case, an expectation recorded from the handler's
own output, a case that does not declare the named breaks, a break whose kept receipt
is missing, green or stale, and a refusal that does not say why. Names, topic paths,
thresholds and remediation live in the validation contract's rule parameters. This
module performs no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from omnibase_core.enums.enum_chain_scenario_break import EnumChainScenarioBreak
from omnibase_core.enums.enum_chain_scenario_kind import EnumChainScenarioKind
from omnibase_core.enums.enum_chain_scenario_oracle_basis import (
    EnumChainScenarioOracleBasis,
)
from omnibase_core.enums.enum_chain_scenario_reading import EnumChainScenarioReading
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_case import (
    ModelChainScenarioCase,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_receipt_set import (
    ModelChainScenarioReceiptSet,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_subcontract import (
    ModelChainScenarioSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = ["check_chain_scenarios"]


def _validate_row(rule: ModelValidatorRule) -> str:
    """Read every parameter of an enabled row before judging any facts."""
    kind = rule_string(rule, "kind")
    rule_string(rule, "remediation")
    rule_string(rule, "declaration_key")
    if kind == "undeclared_node":
        rule_strings(rule, "scope_paths")
    elif kind == "topic_closure":
        rule_strings(rule, "subscribe_paths")
        rule_strings(rule, "publish_paths")
    elif kind == "oracle_basis":
        for name in rule_strings(rule, "refused_bases"):
            EnumChainScenarioOracleBasis(name)
    elif kind == "error_reading":
        EnumChainScenarioReading(rule_string(rule, "required_reading"))
    elif kind == "required_breaks" or kind == "mutation_receipts":
        for key in ("golden_breaks", "error_breaks", "state_update_breaks"):
            for name in rule_strings(rule, key):
                EnumChainScenarioBreak(name)
        if kind == "mutation_receipts":
            rule_string(rule, "red_outcome")
            rule_string(rule, "receipts_file")
    elif kind == "refusal_complete":
        rule_int(rule, "min_reason_chars")
        rule_string(rule, "ticket_prefix")
    elif kind not in ("schema", "golden_coverage", "error_coverage"):
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: unknown kind {kind!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return kind


def _dotted(document: Mapping[str, object], path: str) -> object:
    value: object = document
    for segment in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(segment)
    return value


def _topics(document: Mapping[str, object], paths: Sequence[str]) -> set[str]:
    found: set[str] = set()
    for path in paths:
        value = _dotted(document, path)
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


def _required_breaks(
    rule: ModelValidatorRule, case: ModelChainScenarioCase
) -> tuple[EnumChainScenarioBreak, ...]:
    key = (
        "golden_breaks" if case.kind is EnumChainScenarioKind.GOLDEN else "error_breaks"
    )
    required = [EnumChainScenarioBreak(name) for name in rule_strings(rule, key)]
    if case.state_updates:
        required.extend(
            EnumChainScenarioBreak(name)
            for name in rule_strings(rule, "state_update_breaks")
        )
    return tuple(dict.fromkeys(required))


def _scenario(
    document: Mapping[str, object], key: str
) -> tuple[ModelChainScenarioSubcontract | None, str | None]:
    """The parsed block and no message, no block and no message, or no block and why."""
    raw = document.get(key)
    if raw is None:
        return None, None
    try:
        return ModelChainScenarioSubcontract.model_validate(raw), None
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        return None, f"{key} does not parse at {location or '<root>'}: {first['msg']}"


def _case_issues(
    rule: ModelValidatorRule,
    kind: str,
    path: str,
    document: Mapping[str, object],
    scenario: ModelChainScenarioSubcontract,
    receipts: ModelChainScenarioReceiptSet | None,
) -> list[ModelValidationIssue]:
    issues: list[ModelValidationIssue] = []
    if kind == "topic_closure":
        subscribed = _topics(document, rule_strings(rule, "subscribe_paths"))
        published = _topics(document, rule_strings(rule, "publish_paths"))
        for topic in sorted({case.input.topic for case in scenario.cases} - subscribed):
            issues.append(
                _issue(rule, path, f"input topic {topic!r} is not subscribed")
            )
        declared = {scenario.success_topic}
        declared.update(failure.topic for failure in scenario.failures)
        for case in scenario.cases:
            declared.update(event.topic for event in case.expected_events)
        for topic in sorted(declared - published):
            issues.append(_issue(rule, path, f"topic {topic!r} is not published"))
    elif kind == "golden_coverage":
        covered = {
            case.expected_events[-1].topic
            for case in scenario.cases
            if case.kind is EnumChainScenarioKind.GOLDEN and case.expected_events
        }
        refused = {
            r.subject
            for r in scenario.refusals
            if r.applies_to is EnumChainScenarioKind.GOLDEN
        }
        if scenario.success_topic not in covered | refused:
            issues.append(
                _issue(
                    rule,
                    path,
                    f"success terminal {scenario.success_topic!r} has no golden case ending in it and no refusal",
                )
            )
    elif kind == "error_coverage":
        covered_failures = {
            case.failure
            for case in scenario.cases
            if case.kind is EnumChainScenarioKind.ERROR
        }
        refused_failures = {
            r.subject
            for r in scenario.refusals
            if r.applies_to is EnumChainScenarioKind.ERROR
        }
        for failure in scenario.failures:
            if failure.name not in covered_failures | refused_failures:
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"failure {failure.name!r} has no error case and no refusal",
                    )
                )
    elif kind == "oracle_basis":
        refused = {
            EnumChainScenarioOracleBasis(n) for n in rule_strings(rule, "refused_bases")
        }
        for case in scenario.cases:
            if case.oracle.basis in refused:
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"case {case.case_name!r} takes its expectation from {case.oracle.basis.value}, which is not independent",
                    )
                )
    elif kind == "error_reading":
        required = EnumChainScenarioReading(rule_string(rule, "required_reading"))
        for case in scenario.cases:
            if (
                case.kind is EnumChainScenarioKind.ERROR
                and case.reading is not required
            ):
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"error case {case.case_name!r} expects reading {case.reading}, not {required.value}",
                    )
                )
    elif kind == "required_breaks":
        for case in scenario.cases:
            missing = [b for b in _required_breaks(rule, case) if b not in case.breaks]
            if missing:
                names = ", ".join(b.value for b in missing)
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"case {case.case_name!r} does not declare the break {names}",
                    )
                )
    elif kind == "mutation_receipts":
        red = rule_string(rule, "red_outcome")
        kept = {
            (r.case_name, r.injected_break): r
            for r in (receipts.receipts if receipts else ())
        }
        for case in scenario.cases:
            for needed in _required_breaks(rule, case):
                receipt = kept.get((case.case_name, needed))
                if receipt is None:
                    detail = "has no kept receipt"
                elif receipt.case_hash != case.case_hash():
                    detail = "has a receipt for a different version of the case"
                elif receipt.outcome != red:
                    detail = f"stayed {receipt.outcome} and cannot fail"
                else:
                    continue
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"case {case.case_name!r} under {needed.value} {detail}",
                    )
                )
    elif kind == "refusal_complete":
        minimum = rule_int(rule, "min_reason_chars")
        prefix = rule_string(rule, "ticket_prefix")
        for refusal in scenario.refusals:
            if len(refusal.reason.strip()) < minimum:
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"refusal for {refusal.subject!r} gives a reason under {minimum} characters",
                    )
                )
            if not refusal.unblocked_by.startswith(prefix):
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"refusal for {refusal.subject!r} names no {prefix} ticket",
                    )
                )
    return issues


def check_chain_scenarios(
    documents: Mapping[str, Mapping[str, object]],
    receipts: Mapping[str, ModelChainScenarioReceiptSet | None],
    rules: Sequence[ModelValidatorRule],
) -> list[ModelValidationIssue]:
    """Judge every contract, ordered by rule then contract path."""
    enabled = [rule for rule in rules if rule.enabled]
    kinds = [_validate_row(rule) for rule in enabled]
    parsed: dict[
        tuple[str, str], tuple[ModelChainScenarioSubcontract | None, str | None]
    ] = {}
    issues: list[ModelValidationIssue] = []
    for rule, kind in zip(enabled, kinds, strict=True):
        key = rule_string(rule, "declaration_key")
        for path, document in sorted(documents.items()):
            if (key, path) not in parsed:
                parsed[(key, path)] = _scenario(document, key)
            scenario, problem = parsed[(key, path)]
            if kind == "undeclared_node":
                if (
                    _topics(document, rule_strings(rule, "scope_paths"))
                    and scenario is None
                    and problem is None
                ):
                    issues.append(
                        _issue(
                            rule,
                            path,
                            f"node subscribes to events but declares no {key}",
                        )
                    )
            elif kind == "schema":
                if problem is not None:
                    issues.append(_issue(rule, path, problem))
            elif scenario is not None:
                issues.extend(
                    _case_issues(
                        rule, kind, path, document, scenario, receipts.get(path)
                    )
                )
    return issues
