# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure allowlist stack-shape checker (OMN-21891, one-runtime plan task T1).

Facts in (the data file text, each lane's compose file text), ``ModelValidationIssue`` out: no file
read, no git call, no clock. The allowed services, the per-lane compose file sets, the replica
limit and the baseline are the caller's data file; every message, key list and pattern is a
``parameters`` entry of the matching rule row in ``contracts/stack_shape.validation.yaml``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_stack_shape_data import (
    ModelStackShapeData,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_baseline_moves import carry_baseline
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

RULE_NOT_ALLOWED = "service_not_allowed"
RULE_REPLICAS = "replicas_over_limit"
RULE_FILE_MISSING = "compose_file_missing"
RULE_FILE_UNREADABLE = "compose_file_unreadable"
RULE_DATA_INVALID = "stack_shape_data_invalid"
RULE_BASELINE = "baseline_ratchet"


def _invalid(reason: str) -> ModelOnexError:
    return ModelOnexError(
        message=reason, error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
    )


def _issue(
    rules: Mapping[str, ModelValidatorRule], rule_id: str, path: str, message: str
) -> ModelValidationIssue:
    row = rules[rule_id]
    return ModelValidationIssue(
        severity=row.severity,
        message=" ".join(message.split()),
        code=rule_id,
        file_path=Path(path),
        rule_name=rule_id,
    )


def report(
    rules: Mapping[str, ModelValidatorRule], rule_id: str, path: str, **values: object
) -> tuple[ModelValidationIssue, ...]:
    """One issue of ``rule_id`` from the row's message, or none when the row is disabled."""
    if not _active(rules, rule_id):
        return ()
    message = rule_string(rules[rule_id], "message").format(path=path, **values)
    return (_issue(rules, rule_id, path, message),)


def _active(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> bool:
    row = rules.get(rule_id)
    return row is not None and row.enabled


def validate_rules(rules: Mapping[str, ModelValidatorRule]) -> None:
    """Read every parameter of every enabled row once, so a broken contract fails at load."""
    for required in (RULE_BASELINE, RULE_FILE_UNREADABLE):
        if required not in rules:
            raise _invalid(f"the contract has no {required} rule row")
    for rule_id, row in rules.items():
        if not row.enabled:
            continue
        if rule_id == RULE_REPLICAS:
            rule_strings(row, "replica_keys")
            rule_string(row, "deploy_key")
            rule_string(row, "deploy_replica_key")
            re.compile(rule_string(row, "default_pattern"))
            rule_string(row, "unreadable_message")
        elif rule_id == RULE_FILE_UNREADABLE:
            rule_string(row, "services_key")
            rule_string(row, "removal_marker")
            re.compile(rule_string(row, "removal_pattern"))
            re.compile(rule_string(row, "directive_pattern"))
        elif rule_id == RULE_BASELINE:
            rule_string(row, "data_path")
            rule_string(row, "base_ref")
            rule_int(row, "move_similarity_percent")
            rule_string(row, "key_separator")
            for key in ("missing_message", "unlisted_message", "ticket_message"):
                rule_string(row, key)
            rule_string(row, "growth_message")
            continue
        rule_string(row, "message")


def parse_stack_shape_data(text: str) -> ModelStackShapeData:
    """The allowlist a data file holds; raises ``ModelOnexError`` naming what is malformed."""
    try:
        document = load_yaml_mapping_no_duplicates(text, source="stack-shape data")
    except (yaml.YAMLError, ValueError) as exc:
        raise _invalid(f"not valid YAML ({exc})") from exc
    runtime = document.get("runtime")
    if not isinstance(runtime, dict):
        raise _invalid("runtime must be a mapping holding services and max_replicas")
    max_replicas = runtime.get("max_replicas", 1)
    if isinstance(max_replicas, bool) or not isinstance(max_replicas, int):
        raise _invalid("runtime.max_replicas must be a whole number")
    lanes_raw = document.get("lanes")
    if not isinstance(lanes_raw, dict) or not lanes_raw:
        raise _invalid("lanes must be a non-empty mapping")
    lanes: dict[str, tuple[str, ...]] = {}
    for lane, body in lanes_raw.items():
        files = body.get("compose_files") if isinstance(body, dict) else None
        lanes[str(lane)] = _strings(files, f"lanes.{lane}.compose_files")
    baseline_raw = document.get("baseline") or []
    if not isinstance(baseline_raw, list):
        raise _invalid("baseline must be a list")
    baseline: list[tuple[str, str, str]] = []
    for entry in baseline_raw:
        if not isinstance(entry, dict):
            raise _invalid("every baseline entry must be a mapping")
        file, service = entry.get("file"), entry.get("service")
        if not isinstance(file, str) or not isinstance(service, str):
            raise _invalid("every baseline entry needs a file and a service")
        baseline.append((file, service, str(entry.get("ticket") or "")))
    return ModelStackShapeData(
        runtime_services=frozenset(
            _strings(runtime.get("services"), "runtime.services")
        ),
        max_replicas=max_replicas,
        dependencies=frozenset(
            _strings(document.get("dependencies", []), "dependencies")
        ),
        one_shots=frozenset(_strings(document.get("one_shots", []), "one_shots")),
        lanes=lanes,
        baseline=tuple(baseline),
    )


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _invalid(f"{where} must be a list of strings")
    return tuple(value)


def baseline_key(
    file: str, service: str, rules: Mapping[str, ModelValidatorRule]
) -> str:
    """The identity of one baseline entry."""
    return f"{file}{rule_string(rules[RULE_BASELINE], 'key_separator')}{service}"


def baseline_keys(
    data: ModelStackShapeData, rules: Mapping[str, ModelValidatorRule]
) -> dict[str, int]:
    """Baseline entry -> 1, the shape ``carry_baseline`` allocates over."""
    return {baseline_key(f, s, rules): 1 for f, s, _ in data.baseline}


def lane_files(data: ModelStackShapeData) -> dict[str, tuple[str, ...]]:
    """Compose file -> the lanes whose file set holds it, in lane order."""
    owners: dict[str, list[str]] = {}
    for lane, files in data.lanes.items():
        for file in files:
            owners.setdefault(file, []).append(lane)
    return {file: tuple(lanes) for file, lanes in owners.items()}


def compose_services(
    text: str, rules: Mapping[str, ModelValidatorRule]
) -> dict[str, dict[object, object]]:
    """Service name -> its body; raises ``ModelOnexError`` when the file holds no services mapping."""
    row = rules[RULE_FILE_UNREADABLE]
    key = rule_string(row, "services_key")
    marker = rule_string(row, "removal_marker")
    # compose merge tags are directives to compose, not data: a removed service is not a service
    text = re.sub(
        rule_string(row, "removal_pattern"),
        lambda m: f'{m.group(1)}"{marker}"',
        text,
    )
    text = re.sub(rule_string(row, "directive_pattern"), r"\1", text)
    try:
        # compose reads a repeated key as its last value, as SafeLoader does
        document = yaml.load(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        raise _invalid(str(exc).splitlines()[0]) from exc
    services = document.get(key) if isinstance(document, dict) else None
    if not isinstance(services, dict):
        raise _invalid(f"no {key} mapping")
    return {
        str(name): body if isinstance(body, dict) else {}
        for name, body in services.items()
        if body != marker
    }


def _replica_values(
    body: Mapping[object, object], row: ModelValidatorRule
) -> list[object]:
    values = [body[k] for k in rule_strings(row, "replica_keys") if k in body]
    deploy = body.get(rule_string(row, "deploy_key"))
    if isinstance(deploy, dict):
        key = rule_string(row, "deploy_replica_key")
        if key in deploy:
            values.append(deploy[key])
    return values


def _replica_count(value: object, row: ModelValidatorRule) -> int | None:
    """A declared replica count as a whole number; ``None`` when it cannot be read."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
        default = re.match(rule_string(row, "default_pattern"), text)
        if default:
            return int(default.group(1))
    return None


def check_compose(
    data: ModelStackShapeData,
    path: str,
    services: Mapping[str, Mapping[object, object]],
    lanes: Iterable[str],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for the services of one compose file under the allowlist and the replica limit."""
    issues: list[ModelValidationIssue] = []
    lane_text = ", ".join(lanes)
    baselined = {s for f, s, _ in data.baseline if f == path}
    allowed = data.runtime_services | data.dependencies | data.one_shots | baselined
    for name in sorted(services):
        values = {"service": name, "path": path, "lanes": lane_text}
        if _active(rules, RULE_NOT_ALLOWED) and name not in allowed:
            row = rules[RULE_NOT_ALLOWED]
            issues.append(
                _issue(
                    rules,
                    RULE_NOT_ALLOWED,
                    path,
                    rule_string(row, "message").format(**values),
                )
            )
        if not _active(rules, RULE_REPLICAS) or name not in data.runtime_services:
            continue
        row = rules[RULE_REPLICAS]
        counts: list[int] = []
        for value in _replica_values(services[name], row):
            count = _replica_count(value, row)
            if count is None:
                issues.append(
                    _issue(
                        rules,
                        RULE_REPLICAS,
                        path,
                        rule_string(row, "unreadable_message").format(
                            **values, value=repr(value)
                        ),
                    )
                )
            else:
                counts.append(count)
        if counts and max(counts) > data.max_replicas:
            issues.append(
                _issue(
                    rules,
                    RULE_REPLICAS,
                    path,
                    rule_string(row, "message").format(
                        **values, count=max(counts), limit=data.max_replicas
                    ),
                )
            )
    return tuple(issues)


def check_baseline(
    data: ModelStackShapeData,
    services_by_file: Mapping[str, Iterable[str] | None],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Entries without a ticket, for an unlisted file or for a service that no longer exists."""
    if not _active(rules, RULE_BASELINE):
        return ()
    row = rules[RULE_BASELINE]
    listed = set(lane_files(data))
    issues: list[ModelValidationIssue] = []
    for file, service, ticket in sorted(data.baseline):
        entry = baseline_key(file, service, rules)
        found = services_by_file.get(file)
        if file not in listed:
            message = rule_string(row, "unlisted_message")
        elif found is not None and service not in set(found):
            message = rule_string(row, "missing_message")
        elif not ticket.strip():
            message = rule_string(row, "ticket_message")
        else:
            continue
        issues.append(_issue(rules, RULE_BASELINE, file, message.format(entry=entry)))
    return tuple(issues)


def key_moves(
    head: Iterable[str],
    file_moves: Mapping[str, str],
    rules: Mapping[str, ModelValidatorRule],
) -> dict[str, str]:
    """Baseline entry moves implied by compose file moves (destination -> origin)."""
    separator = rule_string(rules[RULE_BASELINE], "key_separator")
    moves: dict[str, str] = {}
    for key in head:
        file, _, service = key.partition(separator)
        if file in file_moves:
            moves[key] = f"{file_moves[file]}{separator}{service}"
    return moves


def baseline_growth(
    head: Mapping[str, int],
    base: Mapping[str, int],
    file_moves: Mapping[str, str],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Entries the base revision does not allow, after carrying entries over compose file moves."""
    if not _active(rules, RULE_BASELINE):
        return ()
    row = rules[RULE_BASELINE]
    allowances = carry_baseline(head, base, key_moves(head, file_moves, rules))
    separator = rule_string(row, "key_separator")
    return tuple(
        _issue(
            rules,
            RULE_BASELINE,
            key.partition(separator)[0],
            rule_string(row, "growth_message").format(entry=key),
        )
        for key, count in sorted(head.items())
        if count > allowances[key]
    )


__all__ = [
    "RULE_BASELINE",
    "RULE_DATA_INVALID",
    "RULE_FILE_MISSING",
    "RULE_FILE_UNREADABLE",
    "RULE_NOT_ALLOWED",
    "RULE_REPLICAS",
    "baseline_growth",
    "baseline_key",
    "baseline_keys",
    "check_baseline",
    "check_compose",
    "compose_services",
    "key_moves",
    "lane_files",
    "parse_stack_shape_data",
    "report",
    "validate_rules",
]
