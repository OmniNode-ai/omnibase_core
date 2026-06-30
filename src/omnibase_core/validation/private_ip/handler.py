# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerPrivateIpCompute — generated COMPUTE validator for hardcoded private IPs.

GENERATED ARTIFACT (OMN-13294, G2). The scanning logic in ``scan_source`` was
produced by ``node_generation_consumer`` (omnimarket), local-model-first through
the real delegation chain (model ``Qwen3.6-35B-A3B`` on the local-coder backend),
and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_hardcoded_ip``) in the
hardened sandbox: it flagged every ``violation_fixture`` (3 base + 4 adversarial
mutation) and produced zero findings on every ``clean_fixture`` (public IP,
SemVer-shaped token, 172.15 below-band public, suppression-marker line,
contract-sourced endpoint). The corpus verdict — not the LLM's self-report — was
the acceptance authority (memory ``feedback_adversarial_receipts``). See
``GENERATION_PROVENANCE.md`` for the full run.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job (``runtime_private_ip``),
never the handler's — that is what preserves COMPUTE purity (§1A).

The invariant — "a quoted RFC1918 private IPv4 literal in source is a config /
portability leak" — is the SAME one ``node_aislop_sweep`` already detects
advisorily (``_HARDCODED_CONFIG_PATTERNS`` ranges 192.168., 10., 172.16-31); this
validator turns that detection into a BLOCKING gate. The ``onex-allow-internal-ip``
suppression marker is the canonical escape hatch named in CLAUDE.md Rule 6.
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.private_ip.models import (
    ModelPrivateIpFinding,
    ModelPrivateIpScanInput,
    ModelPrivateIpScanResult,
)

__all__ = ["HandlerPrivateIpCompute", "scan_source"]

# Candidate IPv4 literal: four dotted 1-3 digit octets on a word boundary. The
# regex only *finds* candidates; RFC1918 membership is decided by octet parsing
# in ``_rfc1918_block`` so version strings (1.10.172.0) and public IPs (8.8.8.8,
# 172.15.0.1) are correctly excluded — the corpus pins these boundary cases.
_IPV4_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
)

# A line carrying this exact marker is suppressed (allowlisted), matching the
# canonical escape hatch named in CLAUDE.md Rule 6.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-internal-ip"

# A file whose content carries this exact marker anywhere is suppressed in full.
# This is the file-level escape hatch for documentation-heavy source whose
# subject IS private-IP literals (e.g. a module docstring documenting that IP
# hosts are valid in artifact URLs, or a network-restriction model whose example
# data is RFC1918 CIDR ranges) — line markers there would pollute rendered docs.
# Mirrors the test-suite `# onex-allow-file` convention.
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-allow-file-internal-ip"


def _rfc1918_block(o1: int, o2: int, o3: int, o4: int) -> str | None:
    """Return the RFC1918 block label for these octets, or None if not private.

    Pure octet logic — the same membership the aislop ground truth encodes:
      * 10/8        -> first octet 10
      * 172.16/12   -> first octet 172, second octet 16-31 (inclusive)
      * 192.168/16  -> first octet 192, second octet 168
    Any octet > 255 is not a valid IPv4 literal and is not flagged.
    """
    if any(o > 255 for o in (o1, o2, o3, o4)):
        return None
    if o1 == 10:
        return "10/8"
    if o1 == 172 and 16 <= o2 <= 31:
        return "172.16/12"
    if o1 == 192 and o2 == 168:
        return "192.168/16"
    return None


def scan_source(content: str, path: str = "<input>") -> ModelPrivateIpScanResult:
    """Scan ``content`` line by line for hardcoded RFC1918 private-IP literals.

    Pure and deterministic. A line containing the ``onex-allow-internal-ip``
    suppression marker is skipped; otherwise every IPv4 candidate on the line is
    octet-parsed and flagged iff it falls in a private block. Findings are emitted
    in a stable order (line, then column) so the verdict is order-independent
    regardless of dispatch backend (§1A).
    """
    findings: list[ModelPrivateIpFinding] = []
    # File-level escape hatch: a documentation-heavy source whose subject IS
    # private-IP literals suppresses the whole file with one marker, so the
    # findings stay deterministic and the rendered docs stay clean.
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelPrivateIpScanResult(path=path, flagged=False, findings=())
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        for match in _IPV4_CANDIDATE.finditer(line):
            o1, o2, o3, o4 = (int(g) for g in match.groups())
            block = _rfc1918_block(o1, o2, o3, o4)
            if block is None:
                continue
            findings.append(
                ModelPrivateIpFinding(
                    path=path,
                    line=lineno,
                    column=match.start() + 1,
                    matched_text=match.group(),
                    rfc1918_block=block,
                    context=line.rstrip(),
                )
            )
    findings.sort(key=lambda f: (f.line, f.column))
    return ModelPrivateIpScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerPrivateIpCompute:
    """COMPUTE handler: scan one source-text payload for hardcoded private IPs.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-private-ip-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"PrivateIpScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelPrivateIpScanInput]
    ) -> ModelHandlerOutput[ModelPrivateIpScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
