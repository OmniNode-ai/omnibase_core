# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoDirectKafkaProducerCheckCompute — direct-Kafka-producer validation COMPUTE handler.

Ports the AST-based CI gate at
``omniclaude/scripts/validation/validate_no_direct_kafka_producer.py`` into a
canonical COMPUTE node on the def-B ``handle(request) -> response`` shape
(OMN-14355), following the ``node_no_utcnow_check_compute`` template
(OMN-14656).

Architecture: COMPUTE node — pure, deterministic, no I/O. Content arrives via
explicit ``(path, source)`` pairs on the request (see
:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`,
reused rather than forked); the filesystem walk + read happens at the paired
EFFECT boundary (``node_source_file_gather_effect``), never inside this
handler.

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork — ``overall_status`` is computed by
``ModelValidationReport.from_findings()`` using the shared
ERROR > FAIL > WARN > PASS precedence engine. This node emits ``FAIL``
(direct Kafka producer usage) and ``ERROR`` (unparseable file) findings.

Files whose path matches the shared publisher layer (see
:mod:`.visitor_kafka_producer`) are skipped entirely — the oracle's own
per-file exclusion, ported unchanged.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

import ast
from typing import Final, Literal

from omnibase_core.models.nodes.no_direct_kafka_producer_check.model_no_direct_kafka_producer_check_input import (
    ModelNoDirectKafkaProducerCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.visitor_kafka_producer import (
    VALIDATOR_ID,
    DirectKafkaProducerVisitor,
    is_allowed_publisher_path,
)

__all__ = ["NodeNoDirectKafkaProducerCheckCompute"]

# This node has no notion of a "strict"/"advisory" caller profile (it always
# reports FAIL/ERROR findings at face value) — "default" is the precedence
# profile that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoDirectKafkaProducerCheckCompute:
    """COMPUTE handler that AST-scans (path, source) pairs for direct Kafka producer usage."""

    def handle(
        self, request: ModelNoDirectKafkaProducerCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            findings.extend(self._check_file(file.path, file.source))

        embedded_findings = tuple(
            ModelValidationFindingEmbed(**finding.model_dump()) for finding in findings
        )

        return ModelValidationReport.from_findings(
            findings=embedded_findings,
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    def _check_file(self, path: str, source: str) -> list[ModelValidationFinding]:
        """Port of ``check_file`` + the ``is_allowed_path`` skip
        (validate_no_direct_kafka_producer.py:102-132)."""
        if is_allowed_publisher_path(path):
            return []

        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            return [
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    location=path,
                    message=f"{path}: SyntaxError: {exc}",
                    remediation=None,
                )
            ]

        visitor = DirectKafkaProducerVisitor(path)
        visitor.visit(tree)
        return visitor.findings
