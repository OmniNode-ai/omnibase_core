# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker: event-registry drift between a producer and an emit registry (OMN-21416, OMN-21503).

Compares the event registrations a producer declares with the registrations a
consumer's emit registry holds. Both sides arrive as typed
:class:`ModelEventRegistration` values parsed at the validator boundary from
contract-declared sources (OMN-21416); ``ModelValidationIssue`` comes out.

Rules (``rule_id``, each a row of ``contracts/event_registry_drift.validation.yaml``):

* ``event_source_only`` / ``event_registry_only`` -- an event type declared on
  one side only.
* ``topic_source_only`` / ``topic_registry_only`` -- a topic named on one side
  only, across all events.
* ``topics_mismatch``, ``partition_key_mismatch``, ``required_fields_mismatch``
  -- an event on both sides that differs. Required fields compare as a set.
* ``empty_source`` / ``duplicate_registration`` -- input the check cannot
  judge: a side with no registrations, or an event type declared twice on one
  side.

Divergence declared in the baseline is not reported; an event baselined as
one-sided is excluded from field comparison.

No file read, no clock, no environment.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
    ModelEventRegistryDriftCheckInput,
)

RULE_EVENT_SOURCE_ONLY = "event_source_only"
RULE_EVENT_REGISTRY_ONLY = "event_registry_only"
RULE_TOPIC_SOURCE_ONLY = "topic_source_only"
RULE_TOPIC_REGISTRY_ONLY = "topic_registry_only"
RULE_TOPICS_MISMATCH = "topics_mismatch"
RULE_PARTITION_KEY_MISMATCH = "partition_key_mismatch"
RULE_REQUIRED_FIELDS_MISMATCH = "required_fields_mismatch"
RULE_EMPTY_SOURCE = "empty_source"
RULE_DUPLICATE_REGISTRATION = "duplicate_registration"
RULE_SOURCE_UNREADABLE = "source_unreadable"

_Rules = Mapping[str, ModelValidatorRule]


def issue(
    rules: _Rules, rule_id: str, location: str | None, message: str
) -> ModelValidationIssue:
    """One issue under the severity of the ``rule_id`` row."""
    return ModelValidationIssue(
        severity=rules[rule_id].severity,
        message=message,
        code=rule_id,
        file_path=Path(location) if location else None,
        rule_name=rule_id,
    )


def check_event_registry_drift(
    request: ModelEventRegistryDriftCheckInput, rules: _Rules
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one comparison; an input the check cannot judge hides drift."""
    return tuple(_input_errors(request, rules) or _drift(request, rules))


def _input_errors(
    request: ModelEventRegistryDriftCheckInput, rules: _Rules
) -> list[ModelValidationIssue]:
    errors: list[ModelValidationIssue] = []
    for side, registrations in (
        ("source", request.source_registrations),
        ("registry", request.registry_registrations),
    ):
        if not registrations:
            errors.append(
                issue(
                    rules,
                    RULE_EMPTY_SOURCE,
                    None,
                    f"the {side} side declares no event registrations; "
                    "an empty comparison is ERROR, never PASS",
                )
            )
            continue
        counts = Counter(r.event_type for r in registrations)
        for event_type in sorted(t for t, n in counts.items() if n > 1):
            where = sorted(
                r.source for r in registrations if r.event_type == event_type
            )
            errors.append(
                issue(
                    rules,
                    RULE_DUPLICATE_REGISTRATION,
                    where[0],
                    f"{event_type} is declared {counts[event_type]} times on the "
                    f"{side} side ({', '.join(where)}); which one counts is ambiguous",
                )
            )
    return errors


def _drift(
    request: ModelEventRegistryDriftCheckInput, rules: _Rules
) -> list[ModelValidationIssue]:
    baseline = request.baseline
    source = {r.event_type: r for r in request.source_registrations}
    registry = {r.event_type: r for r in request.registry_registrations}
    found: list[ModelValidationIssue] = []

    for event_type in sorted(set(source) - set(registry)):
        if event_type not in baseline.event_source_only:
            found.append(
                issue(
                    rules,
                    RULE_EVENT_SOURCE_ONLY,
                    source[event_type].source,
                    f"{event_type} is declared by the source but missing from the registry",
                )
            )
    for event_type in sorted(set(registry) - set(source)):
        if event_type not in baseline.event_registry_only:
            found.append(
                issue(
                    rules,
                    RULE_EVENT_REGISTRY_ONLY,
                    registry[event_type].source,
                    f"{event_type} is in the registry but no source declares it",
                )
            )

    source_topics = {t for r in source.values() for t in r.topics}
    registry_topics = {t for r in registry.values() for t in r.topics}
    for topic in sorted(source_topics - registry_topics - baseline.source_only_topics):
        found.append(
            issue(
                rules,
                RULE_TOPIC_SOURCE_ONLY,
                None,
                f"topic {topic} is named by the source but by no registry event",
            )
        )
    for topic in sorted(
        registry_topics - source_topics - baseline.registry_only_topics
    ):
        found.append(
            issue(
                rules,
                RULE_TOPIC_REGISTRY_ONLY,
                None,
                f"topic {topic} is named by the registry but by no source event",
            )
        )

    one_sided = baseline.event_source_only | baseline.event_registry_only
    for event_type in sorted((set(source) & set(registry)) - one_sided):
        found.extend(
            _field_drift(source[event_type], registry[event_type], request, rules)
        )
    return found


def _field_drift(
    source: ModelEventRegistration,
    registry: ModelEventRegistration,
    request: ModelEventRegistryDriftCheckInput,
    rules: _Rules,
) -> list[ModelValidationIssue]:
    baseline = request.baseline
    event_type = source.event_type
    found: list[ModelValidationIssue] = []
    source_topics = set(source.topics)
    registry_topics = set(registry.topics)
    if (source_topics - registry_topics) - baseline.source_only_topics or (
        registry_topics - source_topics
    ) - baseline.registry_only_topics:
        found.append(
            issue(
                rules,
                RULE_TOPICS_MISMATCH,
                source.source,
                f"{event_type} topics: source={sorted(source_topics)} "
                f"registry={sorted(registry_topics)}",
            )
        )
    if source.partition_key_field != registry.partition_key_field:
        found.append(
            issue(
                rules,
                RULE_PARTITION_KEY_MISMATCH,
                source.source,
                f"{event_type} partition_key_field: "
                f"source={source.partition_key_field!r} "
                f"registry={registry.partition_key_field!r}",
            )
        )
    if set(source.required_fields) != set(registry.required_fields):
        found.append(
            issue(
                rules,
                RULE_REQUIRED_FIELDS_MISMATCH,
                source.source,
                f"{event_type} required_fields: "
                f"source={sorted(source.required_fields)} "
                f"registry={sorted(registry.required_fields)}",
            )
        )
    return found


__all__ = [
    "RULE_SOURCE_UNREADABLE",
    "check_event_registry_drift",
    "issue",
]
