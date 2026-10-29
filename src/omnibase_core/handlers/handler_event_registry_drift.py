# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerEventRegistryDrift — event-registry drift validation in the generic validator format.

Compares the event registrations a producer declares with the registrations a
consumer's emit registry holds, on the def-B ``handle(request) -> response``
shape (OMN-14355). It replaces the AST reading of one repository's registry
literal in another repository's drift check (OMN-21416): both sides arrive as
typed :class:`ModelEventRegistration` values, parsed at the CLI boundary from
contract-declared sources.

Findings (``rule_id``):

* ``FAIL`` ``event_source_only`` / ``event_registry_only`` — an event type
  declared on one side only.
* ``FAIL`` ``topic_source_only`` / ``topic_registry_only`` — a topic named on
  one side only, across all events.
* ``FAIL`` ``topics_mismatch``, ``partition_key_mismatch``,
  ``required_fields_mismatch`` — an event on both sides that differs.
  Required fields compare as a set.
* ``ERROR`` ``empty_source`` / ``duplicate_registration`` — input the check
  cannot judge: a side with no registrations, or an event type declared twice
  on one side.

Divergence declared in the baseline is not reported; an event baselined as
one-sided is excluded from field comparison.

Pure — no filesystem access, no clock, no global state.
"""

from __future__ import annotations

from collections import Counter
from typing import Final, Literal

from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
    ModelEventRegistryDriftCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["VALIDATOR_ID", "HandlerEventRegistryDrift"]

VALIDATOR_ID: Final[str] = "event_registry_drift"

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"

_Severity = Literal["FAIL", "ERROR"]


def _finding(
    rule_id: str, severity: _Severity, location: str | None, message: str
) -> ModelValidationFinding:
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity=severity,
        location=location,
        message=message,
        remediation=None,
        rule_id=rule_id,
    )


class HandlerEventRegistryDrift:
    """Compares two sets of event registrations."""

    def handle(
        self, request: ModelEventRegistryDriftCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        findings = self._input_errors(request) or self._drift(request)
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                for finding in findings
            ),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    def _input_errors(
        self, request: ModelEventRegistryDriftCheckInput
    ) -> list[ModelValidationFinding]:
        errors: list[ModelValidationFinding] = []
        for side, registrations in (
            ("source", request.source_registrations),
            ("registry", request.registry_registrations),
        ):
            if not registrations:
                errors.append(
                    _finding(
                        "empty_source",
                        "ERROR",
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
                    _finding(
                        "duplicate_registration",
                        "ERROR",
                        where[0],
                        f"{event_type} is declared {counts[event_type]} times on the "
                        f"{side} side ({', '.join(where)}); which one counts is ambiguous",
                    )
                )
        return errors

    def _drift(
        self, request: ModelEventRegistryDriftCheckInput
    ) -> list[ModelValidationFinding]:
        baseline = request.baseline
        source = {r.event_type: r for r in request.source_registrations}
        registry = {r.event_type: r for r in request.registry_registrations}
        findings: list[ModelValidationFinding] = []

        for event_type in sorted(set(source) - set(registry)):
            if event_type not in baseline.event_source_only:
                findings.append(
                    _finding(
                        "event_source_only",
                        "FAIL",
                        source[event_type].source,
                        f"{event_type} is declared by the source but missing from the registry",
                    )
                )
        for event_type in sorted(set(registry) - set(source)):
            if event_type not in baseline.event_registry_only:
                findings.append(
                    _finding(
                        "event_registry_only",
                        "FAIL",
                        registry[event_type].source,
                        f"{event_type} is in the registry but no source declares it",
                    )
                )

        source_topics = {t for r in source.values() for t in r.topics}
        registry_topics = {t for r in registry.values() for t in r.topics}
        for topic in sorted(
            source_topics - registry_topics - baseline.source_only_topics
        ):
            findings.append(
                _finding(
                    "topic_source_only",
                    "FAIL",
                    None,
                    f"topic {topic} is named by the source but by no registry event",
                )
            )
        for topic in sorted(
            registry_topics - source_topics - baseline.registry_only_topics
        ):
            findings.append(
                _finding(
                    "topic_registry_only",
                    "FAIL",
                    None,
                    f"topic {topic} is named by the registry but by no source event",
                )
            )

        one_sided = baseline.event_source_only | baseline.event_registry_only
        for event_type in sorted((set(source) & set(registry)) - one_sided):
            findings.extend(
                self._field_drift(source[event_type], registry[event_type], request)
            )
        return findings

    def _field_drift(
        self,
        source: ModelEventRegistration,
        registry: ModelEventRegistration,
        request: ModelEventRegistryDriftCheckInput,
    ) -> list[ModelValidationFinding]:
        baseline = request.baseline
        event_type = source.event_type
        findings: list[ModelValidationFinding] = []
        source_topics = set(source.topics)
        registry_topics = set(registry.topics)
        if (source_topics - registry_topics) - baseline.source_only_topics or (
            registry_topics - source_topics
        ) - baseline.registry_only_topics:
            findings.append(
                _finding(
                    "topics_mismatch",
                    "FAIL",
                    source.source,
                    f"{event_type} topics: source={sorted(source_topics)} "
                    f"registry={sorted(registry_topics)}",
                )
            )
        if source.partition_key_field != registry.partition_key_field:
            findings.append(
                _finding(
                    "partition_key_mismatch",
                    "FAIL",
                    source.source,
                    f"{event_type} partition_key_field: "
                    f"source={source.partition_key_field!r} "
                    f"registry={registry.partition_key_field!r}",
                )
            )
        if set(source.required_fields) != set(registry.required_fields):
            findings.append(
                _finding(
                    "required_fields_mismatch",
                    "FAIL",
                    source.source,
                    f"{event_type} required_fields: "
                    f"source={sorted(source.required_fields)} "
                    f"registry={sorted(registry.required_fields)}",
                )
            )
        return findings
