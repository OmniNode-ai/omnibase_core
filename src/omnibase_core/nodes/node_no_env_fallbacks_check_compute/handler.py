# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoEnvFallbacksCheckCompute — localhost/hardcoded-endpoint-fallback validation COMPUTE handler.

Ports the canonical unified CI gate at
``omniclaude/scripts/validate_no_env_fallbacks.py`` into a canonical COMPUTE
node on the def-B ``handle(request) -> response`` shape (OMN-14355),
following the ``node_no_utcnow_check_compute`` template (OMN-14656).

Architecture: COMPUTE node — pure, deterministic, no I/O. Content arrives via
explicit ``(path, source)`` pairs on the request (see
:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`,
reused rather than forked); the filesystem walk + read happens at the paired
EFFECT boundary (``node_source_file_gather_effect``), never inside this
handler.

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork. This node only ever emits ``FAIL`` findings (a fallback
default was found), so with the ``"default"`` profile the precedence engine
gives ``overall_status == "FAIL"`` whenever any finding is present and
``"PASS"`` otherwise.

Per-finding message text reproduces the CI gate's flagged-line text
byte-for-byte; see :mod:`.matcher_env_fallbacks` for the port.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

from typing import Final, Literal

from omnibase_core.models.nodes.no_env_fallbacks_check.model_no_env_fallbacks_check_input import (
    ModelNoEnvFallbacksCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_env_fallbacks_check_compute.matcher_env_fallbacks import (
    VALIDATOR_ID,
    find_env_fallback_violations,
)

__all__ = ["NodeNoEnvFallbacksCheckCompute"]

# This node has no notion of a "strict"/"advisory" caller profile (it always
# reports FAIL findings at face value) — "default" is the precedence profile
# that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoEnvFallbacksCheckCompute:
    """COMPUTE handler that line-scans (path, source) pairs for endpoint fallback defaults."""

    def handle(self, request: ModelNoEnvFallbacksCheckInput) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — pure, no I/O, no clock.
        """
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            findings.extend(self._check_file(file.path, file.source))

        embedded_findings = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for finding in findings
        )

        return ModelValidationReport.from_findings(
            findings=embedded_findings,
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    def _check_file(self, path: str, source: str) -> list[ModelValidationFinding]:
        """Port of the per-file dispatch + scan (validate_no_env_fallbacks.py:202-243)."""
        return find_env_fallback_violations(path, source)
