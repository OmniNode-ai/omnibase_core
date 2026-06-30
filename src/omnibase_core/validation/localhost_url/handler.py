# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerLocalhostUrlCompute — generated COMPUTE validator for hardcoded localhost URLs.

GENERATED ARTIFACT (OMN-13480 residual of OMN-13294, G2). The scanning logic in
``scan_source`` was produced by ``node_generation_consumer`` (omnimarket),
local-model-first through the real delegation chain (model ``Qwen3.6-35B-A3B`` on
the local-coder backend), and accepted ONLY because it passed a deterministic
acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_hardcoded_localhost_url``) in
the hardened sandbox: it flagged every ``violation_fixture`` (2 base + 3 adversarial
mutation) and produced zero findings on every ``clean_fixture`` (public host URL,
contract-sourced endpoint reference, bare ``localhost`` prose word, a public host
whose NAME merely contains ``localhost``, and a suppression-marker line). The corpus
verdict — not the LLM's self-report — was the acceptance authority (memory
``feedback_adversarial_receipts``). See ``GENERATION_PROVENANCE.md`` for the full run.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job (``runtime_localhost_url``),
never the handler's — that is what preserves COMPUTE purity (§1A).

The invariant — "a quoted ``http(s)://localhost`` or ``http(s)://127.0.0.1`` URL
literal in source is a config / portability leak (an endpoint that only resolves on
the author's box, never in CI / containers / the .201 server)" — is the SAME one
``node_aislop_sweep`` already detects advisorily and the CLAUDE.md "All URLs from
contracts only" rule (epic OMN-12803) names durably; this validator turns that into
a BLOCKING gate. It is the COMPLEMENT of ``validator_url_authority``: url-authority's
``public-https-literal`` rule deliberately EXCLUDES localhost/loopback, and its
``url-const-assignment`` rule only catches a loopback literal assigned to a
``*_URL`` / ``*_ENDPOINT`` constant — a loopback URL in any OTHER context (a call
arg, a dict value, a list element, a non-URL-named variable) is uncovered. This
validator flags ANY ``http(s)://localhost|127.0.0.1`` literal regardless of context.
The ``onex-allow-internal-ip`` suppression marker is the canonical escape hatch
named in CLAUDE.md Rule 6 (shared with the private-IP validator — both guard
loopback/LAN endpoint leaks).
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.localhost_url.models import (
    ModelLocalhostUrlFinding,
    ModelLocalhostUrlScanInput,
    ModelLocalhostUrlScanResult,
)

__all__ = ["HandlerLocalhostUrlCompute", "scan_source"]

# Loopback-URL literal: an http(s):// scheme followed by EXACTLY the host
# ``localhost`` or ``127.0.0.1``, terminated by a port/path/query/fragment
# delimiter or the end of the literal. The trailing negative lookahead
# ``(?![\w.-])`` is the precision boundary: it ensures the host is EXACTLY the
# loopback host and not the prefix of a longer hostname — so
# ``https://localhost-mirror.example.com`` (host ``localhost-mirror``) and
# ``https://127.0.0.1.evil.com`` are NOT matched, while ``http://localhost:8000``,
# ``http://localhost/metrics``, and ``https://127.0.0.1/api`` (and the bare
# ``http://localhost`` at end of literal) all match. The host is captured in
# group ``host`` for the finding.
_LOOPBACK_URL: Final[re.Pattern[str]] = re.compile(
    r"https?://(?P<host>localhost|127\.0\.0\.1)(?![\w.-])"
)

# A line carrying this exact marker is suppressed (allowlisted), matching the
# canonical escape hatch named in CLAUDE.md Rule 6 (shared with the private-IP
# validator — both guard loopback / LAN endpoint leaks).
_SUPPRESSION_MARKER: Final[str] = "onex-allow-internal-ip"

# A file whose content carries this exact marker anywhere is suppressed in full.
# File-level escape hatch for documentation-heavy source whose subject IS
# localhost-URL literals (e.g. a runbook documenting local dev endpoints, or this
# validator's own corpus/provenance docs) — line markers there would pollute
# rendered docs. Mirrors the private-IP validator's file-level convention.
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-allow-file-internal-ip"


def scan_source(content: str, path: str = "<input>") -> ModelLocalhostUrlScanResult:
    """Scan ``content`` line by line for hardcoded localhost/loopback URL literals.

    Pure and deterministic. A line containing the ``onex-allow-internal-ip``
    suppression marker is skipped; otherwise every ``http(s)://localhost`` /
    ``http(s)://127.0.0.1`` literal on the line is flagged. The trailing
    word-boundary lookahead excludes hostnames that merely START with the loopback
    token (``localhost-mirror``, ``127.0.0.1.evil.com``). Findings are emitted in a
    stable order (line, then column) so the verdict is order-independent regardless
    of dispatch backend (§1A).
    """
    findings: list[ModelLocalhostUrlFinding] = []
    # File-level escape hatch: a documentation-heavy source whose subject IS
    # localhost-URL literals suppresses the whole file with one marker, so the
    # findings stay deterministic and the rendered docs stay clean.
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelLocalhostUrlScanResult(path=path, flagged=False, findings=())
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        for match in _LOOPBACK_URL.finditer(line):
            findings.append(
                ModelLocalhostUrlFinding(
                    path=path,
                    line=lineno,
                    column=match.start() + 1,
                    matched_url=match.group(),
                    host=match.group("host"),
                    context=line.rstrip(),
                )
            )
    findings.sort(key=lambda f: (f.line, f.column))
    return ModelLocalhostUrlScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerLocalhostUrlCompute:
    """COMPUTE handler: scan one source-text payload for hardcoded localhost URLs.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-localhost-url-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"LocalhostUrlScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelLocalhostUrlScanInput]
    ) -> ModelHandlerOutput[ModelLocalhostUrlScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
