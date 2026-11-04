# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure error-rule schema, authority and static action-closure checks (OMN-19998)."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.error_rule_table.model_error_action_contract import (
    ModelErrorActionContract,
)
from omnibase_core.models.error_rule_table.model_error_rule_check_input import (
    ModelErrorRuleCheckInput,
)
from omnibase_core.models.error_rule_table.model_error_rule_none_result import (
    ModelErrorRuleNoneResult,
)
from omnibase_core.models.error_rule_table.model_error_rule_policy import (
    ModelErrorRulePolicy,
)
from omnibase_core.models.error_rule_table.model_error_rule_row import ModelErrorRuleRow


def _invalid(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def action_contract_digest(
    contract_id: str, contracts: Mapping[str, ModelErrorActionContract]
) -> str:
    """Hash effective configuration plus every reachable contract; refuse missing nodes and cycles.

    Child digests are part of the parent digest, including shared descendants. A new
    edge therefore changes the digest even if it reaches an already reachable node.
    """
    active: set[str] = set()
    cached: dict[str, str] = {}

    def visit(node_id: str) -> str:
        if node_id in active:
            raise _invalid(f"action.contract.calls: cycle at {node_id}")
        if node_id not in contracts:
            raise _invalid(f"action.contract.calls: missing contract {node_id}")
        if node_id in cached:
            return cached[node_id]
        node = contracts[node_id]
        if node.id != node_id:
            raise _invalid(
                f"action.contract.id: registry key {node_id} differs from {node.id}"
            )
        active.add(node_id)
        closure = {child: visit(child) for child in sorted(node.calls)}
        payload = {"contract": node.model_dump(mode="json"), "closure": closure}
        digest = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
        active.remove(node_id)
        cached[node_id] = digest
        return digest

    return visit(contract_id)


def error_rule_policy(request: ModelErrorRuleCheckInput) -> ModelErrorRulePolicy:
    """Read the required rule parameters; absent or malformed policy fails closed."""
    rules = [
        r for r in request.contract.rules if r.rule_id == "error_rule_table_invalid"
    ]
    if (
        len(rules) != 1
        or not rules[0].enabled
        or not rules[0].severity.is_error_or_above()
    ):
        raise _invalid("error_rule_table_invalid: one enabled error rule is required")
    return ModelErrorRulePolicy.model_validate(rules[0].parameters)


def check_error_rule_table(
    request: ModelErrorRuleCheckInput,
) -> tuple[ModelValidationIssue, ...]:
    """Return field-named diagnostics for every row; do no I/O and dispatch nothing."""
    policy = error_rule_policy(request)
    rule = next(
        r for r in request.contract.rules if r.rule_id == "error_rule_table_invalid"
    )
    issues: list[ModelValidationIssue] = []

    def refuse(field: str, reason: str) -> None:
        issues.append(
            ModelValidationIssue(
                severity=rule.severity,
                code=rule.rule_id,
                rule_name=rule.rule_id,
                message=policy.message.format(field=field, reason=reason),
                context={"field": field},
            )
        )

    if set(request.document) != {"error_rules"}:
        refuse("error_rules", "the table document must contain only error_rules")
    raw_rows = request.document.get("error_rules")
    if not isinstance(raw_rows, list):
        refuse("error_rules", "must be a list of explicit rows")
        return tuple(issues)
    if not raw_rows:
        refuse("error_rules", "requires an explicit row, never silence")
    ids: set[str] = set()
    keys: set[str] = set()
    for index, raw in enumerate(raw_rows):
        prefix = f"error_rules[{index}]"
        try:
            row = ModelErrorRuleRow.model_validate(raw)
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"])
                refuse(f"{prefix}.{location}", error["msg"])
            continue

        def reject(field: str, reason: str, prefix: str = prefix) -> None:
            refuse(f"{prefix}.{field}", reason)

        if row.id in ids:
            reject("id", f"duplicate stable id {row.id}")
        ids.add(row.id)
        if row.id in request.retired_ids:
            reject("id", f"retired stable id {row.id} cannot be reused")
        for key in row.class_keys:
            if not key.strip():
                reject("class_keys", "keys cannot be blank")
            if key in keys:
                reject(
                    "class_keys",
                    f"duplicate class key {key} at key_version {row.key_version}",
                )
            keys.add(key)
        for name, value, allowed in (
            ("mode", row.mode, policy.modes),
            ("trigger.kind", row.trigger.kind, policy.trigger_kinds),
            ("break_class", row.break_class, policy.break_classes),
            ("subject_kind", row.subject_kind, policy.subject_kinds),
        ):
            if value not in allowed:
                reject(name, f"unregistered value {value}")
        if (
            row.mode != policy.shadow_mode
            and request.authorized_modes.get(row.id) != row.mode
        ):
            reject("mode", "requires a trusted human PR mode authorization")
        if row.trigger.kind == policy.state_trigger:
            if row.trigger.state_check not in request.registered_state_checks:
                reject("trigger.state_check", "must name a registered state check")
        elif row.trigger.state_check is not None:
            reject("trigger.state_check", "only a state trigger names a state check")
        if (
            row.read_back
            and row.read_back.state_check not in request.registered_state_checks
        ):
            reject("read_back.state_check", "must name a registered state check")

        if row.source_state is not None:
            if (
                row.source_state != policy.needs_source
                or row.mode != policy.shadow_mode
            ):
                reject("source_state", "needs-source is shadow-only")
            if row.sources:
                reject(
                    "source_state", "needs-source must not conceal unresolved sources"
                )
        if not row.sources and row.source_state != policy.needs_source:
            reject("sources", "requires a resolvable ruling timestamp or ticket")
        primary_sources = []
        for source in row.sources:
            if re.fullmatch(policy.source_pointer_pattern, source):
                continue
            primary_sources.append(source)
            if (
                not re.fullmatch(policy.source_pattern, source)
                or source not in request.resolved_sources
            ):
                reject("sources", f"unresolved primary source {source}")
        if row.sources and not primary_sources:
            reject("sources", "a memory pointer is never the only source")
        for field, records in (
            ("fixtures.positive", row.fixtures.positive),
            ("fixtures.negative", row.fixtures.negative),
        ):
            if any(not record.strip() for record in records):
                reject(field, "record ids cannot be blank")
        if set(row.fixtures.positive) & set(row.fixtures.negative):
            reject("fixtures.negative", "a negative record cannot also be positive")
        if any(not kind.strip() for kind in row.lane_kinds):
            reject("lane_kinds", "lane kinds cannot be blank")
        if row.mode == policy.dispatch_mode and row.measured is None:
            reject("measured", "dispatch requires a measured replay block")
        if row.measured:
            measured = row.measured
            if measured.written_by != policy.measurement_writer:
                reject(
                    "measured.written_by",
                    "only the registered measurement node writes measured",
                )
            if (
                measured.interval_start.tzinfo is None
                or measured.interval_end.tzinfo is None
            ):
                reject("measured.interval", "requires timezone-aware bounds")
            elif measured.interval_end <= measured.interval_start:
                reject("measured.interval", "end must be after start")
            if measured.false_matches > measured.hits:
                reject("measured.false_matches", "cannot exceed hits")
            if request.measurements.get(row.id) != measured:
                reject(
                    "measured",
                    "measurement differs from the trusted measurement-node record",
                )

        action = row.action
        if action.kind == policy.terminal_kind:
            if not action.reason or not action.reason.strip():
                reject("action.reason", "none requires a reason")
            if not row.sources:
                reject(
                    "sources", "none requires a resolved source, including in shadow"
                )
            if action.contract is not None or action.digest is not None:
                reject(
                    "action.contract", "none cannot name an action contract or digest"
                )
            if row.read_back is not None:
                reject("read_back", "none cannot name a read-back")
            continue
        if action.kind not in policy.registered_actions:
            reject("action.kind", f"unregistered action {action.kind}")
            continue
        contract_id = action.contract
        if contract_id is None or contract_id != action.kind:
            reject(
                "action.contract",
                "must name its registered action contract, never a node or command",
            )
            continue
        if action.reason is not None:
            reject("action.reason", "only none carries a terminal reason")
        if row.read_back is None:
            reject(
                "read_back",
                "an executable action requires a registered failure read-back",
            )
        if (
            action.kind == policy.backlog_action
            and row.subject_kind == policy.pr_subject
        ):
            reject("subject_kind", "PR workers are reached only through landing-intent")
        try:
            digest = action_contract_digest(contract_id, request.action_contracts)
        except ModelOnexError as exc:
            reject("action.contract", str(exc))
            continue
        if action.digest != digest:
            reject(
                "action.digest",
                "static call closure or effective configuration changed",
            )
        visited: set[str] = set()
        pending = [contract_id]
        while pending:
            node_id = pending.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            node = request.action_contracts[node_id]
            for capability in node.capabilities:
                if capability in policy.forbidden_capabilities:
                    reject(
                        "action.contract.capabilities",
                        f"{node_id} declares forbidden capability {capability}",
                    )
            if not set(node.targets) <= set(policy.allowed_targets):
                reject(
                    "action.contract.targets",
                    f"{node_id} reaches targets outside the allowed environments",
                )
            if set(node.scope_marker) != set(policy.scope_marker):
                reject(
                    "action.contract.scope_marker",
                    f"{node_id} does not propagate the required scope marker",
                )
            if any(not key.strip() for key in node.idempotent_by):
                reject(
                    "action.contract.idempotent_by",
                    f"{node_id} requires a nonblank natural key",
                )
            pending.extend(node.calls)
    return tuple(issues)


def none_rule_result(
    request: ModelErrorRuleCheckInput, rule_id: str
) -> ModelErrorRuleNoneResult:
    """Project a validated none match to its terminal result; never produce work.

    The matcher calls this after matching the exact key and structured conditions.
    Revalidation here prevents a terminal result from being built from an invalid row.
    """
    issues = check_error_rule_table(request)
    if issues:
        raise _invalid("; ".join(issue.message for issue in issues))
    policy = error_rule_policy(request)
    raw_rows = request.document["error_rules"]
    if not isinstance(raw_rows, list):
        raise _invalid("error_rules: expected rows")
    for raw in raw_rows:
        row = ModelErrorRuleRow.model_validate(raw)
        if row.id == rule_id:
            if row.action.kind != policy.terminal_kind:
                raise _invalid(
                    "action.kind: only a none row has a terminal none result"
                )
            return ModelErrorRuleNoneResult(
                rule_name=row.id,
                message=f"{policy.terminal_prefix} {row.action.reason}",
            )
    raise _invalid(f"id: no row named {rule_id}")
