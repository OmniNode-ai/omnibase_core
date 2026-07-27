# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeNoHardcodedIpCheckCompute — hardcoded-internal-IP validation COMPUTE handler.

Ports the line-scan CI gate at
``omniclaude/scripts/validation/validate_no_hardcoded_ip.py`` into a canonical
COMPUTE node on the def-B ``handle(request) -> response`` shape (OMN-14355),
following the ``node_no_utcnow_check_compute`` template (OMN-14656).

Architecture: COMPUTE node — pure, deterministic, no I/O. Content arrives via
explicit ``(path, source)`` pairs on the request (see
:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`,
reused rather than forked);
the filesystem walk + read happens at the paired EFFECT boundary
(``node_source_file_gather_effect``), never inside this handler.

Output shape: the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), NOT a
per-node fork. This node only ever emits ``FAIL`` findings (a hardcoded
internal IP was found), so with the ``"default"`` profile the precedence
engine gives ``overall_status == "FAIL"`` whenever any finding is present and
``"PASS"`` otherwise.

Per-finding message text reproduces the CI gate's flagged-line text
byte-for-byte; see :mod:`.matcher_hardcoded_ip` for the port.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

from typing import Final, Literal

from omnibase_core.models.nodes.no_hardcoded_ip_check.model_no_hardcoded_ip_check_input import (
    ModelNoHardcodedIpCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_no_hardcoded_ip_check_compute.matcher_hardcoded_ip import (
    VALIDATOR_ID,
    find_hardcoded_ip_violations,
)

__all__ = ["NodeNoHardcodedIpCheckCompute"]

# This node has no notion of a "strict"/"advisory" caller profile (it always
# reports FAIL findings at face value) — "default" is the precedence profile
# that leaves findings unmodified before aggregation.
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class NodeNoHardcodedIpCheckCompute:
    """COMPUTE handler that line-scans (path, source) pairs for hardcoded internal IPs."""

    def handle(self, request: ModelNoHardcodedIpCheckInput) -> ModelValidationReport:
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
        """Port of the per-file scan loop (validate_no_hardcoded_ip.py:49-57)."""
        return find_hardcoded_ip_violations(path, source)
