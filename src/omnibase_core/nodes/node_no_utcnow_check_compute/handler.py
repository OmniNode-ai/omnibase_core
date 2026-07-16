# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoUtcnowCheckCompute — no-utcnow-usage validation COMPUTE handler.

Ports the AST-based CI gate at
``omniclaude/scripts/validation/validate_no_utcnow.py`` into a canonical
COMPUTE node on the def-B ``handle(request) -> response`` shape (OMN-14355).

Architecture: COMPUTE node — pure, deterministic, no I/O. Content arrives via
explicit ``(path, source)`` pairs on the request (see
:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`);
the filesystem walk + read happens at the paired EFFECT boundary
(``node_source_file_gather_effect``), never inside this handler.

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork — ``overall_status`` is computed by
``ModelValidationReport.from_findings()`` using the shared
ERROR > FAIL > WARN > PASS precedence engine rather than a bespoke
aggregation rule. This node only ever emits ``FAIL`` (utcnow violation) and
``ERROR`` (unparseable file) findings, so with the ``"default"`` profile the
precedence engine gives ``overall_status == "ERROR"`` when any file fails to
parse (ERROR outranks FAIL) and ``"FAIL"`` when only utcnow violations are
present — a more precise aggregate signal than the prior fork's
FAIL-for-either collapse.

Per-finding message text (including the U+2014 em dash) is reproduced
byte-for-byte against the CI gate; see :mod:`.visitor_utcnow` for the
fidelity note on the over-broad ``*.utcnow`` match.

Ticket: OMN-14656 (RSD canary — Characterize -> Generate two-node split).
"""

from __future__ import annotations

import ast
from typing import Final, Literal

from omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input import (
    ModelNoUtcnowCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_utcnow_check_compute.visitor_utcnow import (
    VALIDATOR_ID,
    UtcNowVisitor,
)

__all__ = ["NodeNoUtcnowCheckCompute"]

# This node has no notion of a "strict"/"advisory" caller profile (it always
# reports FAIL/ERROR findings at face value) — "default" is the precedence
# profile that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoUtcnowCheckCompute:
    """COMPUTE handler that AST-scans (path, source) pairs for utcnow usage."""

    def handle(self, request: ModelNoUtcnowCheckInput) -> ModelValidationReport:
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
        """Port of ``check_file`` (validate_no_utcnow.py:63-72)."""
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

        visitor = UtcNowVisitor(path)
        visitor.visit(tree)
        return visitor.findings
