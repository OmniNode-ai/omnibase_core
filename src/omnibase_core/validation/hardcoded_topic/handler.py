# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerHardcodedTopicCompute — generated COMPUTE validator for hardcoded onex.* topics.

GENERATED ARTIFACT (OMN-13294, G2 SEA-dogfood). The scanning regex in
``scan_source`` was produced by ``HandlerGenerationConsumer``
(``node_generation_consumer``, omnimarket), local-model-first through the real
delegation chain against the live model (``Qwen3.6-35B-A3B`` on the local-coder
backend at ``http://192.168.86.201:8000/v1/chat/completions``),  # onex-allow-internal-ip OMN-13294 provenance: the live generation backend endpoint
and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_hardcoded_topic.HARDCODED_TOPIC_CORPUS``)
in the hardened sandbox on the FIRST attempt: it flagged every
``violation_fixture`` (2 base + 3 adversarial mutation: single-quote, other-domain
suffix, deeper 5-segment) and produced zero findings on every ``clean_fixture``
(contract-resolved topic, dotted python import path, two-segment ``onex.core``
below the topic shape, a non-``onex`` dotted ``kafka.cluster.broker.id`` string).
The corpus verdict — not the LLM's self-report — was the acceptance authority
(memory ``feedback_adversarial_receipts``). See ``GENERATION_PROVENANCE.md`` for
the full run; the raw generated ``handle(input_data)`` is committed verbatim in
``docs/evidence/hardcoded-topic-string/hardcoded-topic-string.generation.json``.

The core scan is the regex ``(['"])onex\\.[a-z0-9]+\\.[a-z0-9]+\\.[a-z0-9]+
(?:\\.[a-z0-9]+)*\\1`` over each line — the SAME ``onex.<a>.<b>.<c>`` topic shape
``node_aislop_sweep._HARDCODED_TOPIC_PATTERN`` already encodes advisorily. The
quote backreference (``\\1``) ties the closing quote to the opening one so a
partial / mismatched-quote fragment cannot match. This handler turns that
advisory detection into a BLOCKING gate (OMN-13294).

Hand-hardening applied to the corpus-accepted seed (the seed is a SEED, not
drop-in):

* Structured the raw ``handle(input_data)`` dict-return into the canonical
  ``line`` / ``topic`` / ``context`` finding shape (mirrors the sibling
  private-IP / unfinished-work-marker validators).
* Added line-level (``# onex-allow-topic-literal``) and file-level
  (``# onex-allow-file-topic-literal``) escape hatches so the canonical topic
  registry / contract-fixture sources whose SUBJECT is the topic literal are not
  false-flagged (e.g. ``constants_event_types.py``, this validator's own corpus
  test). Mirrors the unfinished-work-marker validator's two-tier suppression.
* The ``re.IGNORECASE`` flag the model emitted is DROPPED: onex topics are
  lowercase by contract (``constants_event_types`` and the aislop ground truth
  are both lowercase-only), and case-insensitivity would let an uppercased
  decoy slip the boundary in the other direction. Lowercase-only matches the
  corpus and the ground truth exactly.
* Findings are emitted in source order (line, then in-line match order) so the
  verdict is order-independent regardless of dispatch backend (§1A).

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job
(``runtime_hardcoded_topic``), never the handler's — that is what preserves
COMPUTE purity (§1A).
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.hardcoded_topic.models import (
    ModelHardcodedTopicFinding,
    ModelHardcodedTopicScanInput,
    ModelHardcodedTopicScanResult,
)

__all__ = ["HandlerHardcodedTopicCompute", "scan_source"]

# Quoted onex.<a>.<b>.<c>(.<d>...) topic literal: at least three dot-separated
# lowercase-alphanumeric segments after the ``onex`` prefix, enclosed in matching
# quotes. The quote backreference (\1) ties the closing quote to the opening one,
# so a mismatched-quote fragment cannot match. This is the EXACT shape
# node_aislop_sweep._HARDCODED_TOPIC_PATTERN encodes (the hand-authored ground
# truth) — preserved verbatim from the corpus-accepted generated seed, minus the
# model's IGNORECASE flag (onex topics are lowercase by contract).
_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""(['"])onex\.[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+(?:\.[a-z0-9]+)*\1"""
)

# A line carrying this exact marker is suppressed (allowlisted) — the canonical
# line-level escape hatch for an approved, source-of-truth topic declaration (a
# topic-registry constant) or a ticket-referenced exception.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-topic-literal"

# A file whose content carries this exact marker anywhere is suppressed in full.
# File-level escape hatch for the canonical topic registry / contract-fixture
# source whose SUBJECT is topic literals (e.g. constants_event_types.py, this
# validator's own corpus test) — line markers there would pollute the rendered
# declarations. Mirrors the unfinished-work-marker validator's file-level convention.
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-allow-file-topic-literal"


def scan_source(content: str, path: str = "<input>") -> ModelHardcodedTopicScanResult:
    """Scan ``content`` line by line for hardcoded ``onex.*`` topic literals.

    Pure and deterministic. A line containing the ``onex-allow-topic-literal``
    suppression marker is skipped; a file containing the
    ``onex-allow-file-topic-literal`` marker is suppressed entirely. Otherwise
    every quoted ``onex.<a>.<b>.<c>`` topic literal on the line is flagged.
    Findings are emitted in a stable order (line, then in-line match order) so the
    verdict is order-independent regardless of dispatch backend (§1A).
    """
    # File-level escape hatch: a topic-registry / contract-fixture source whose
    # subject IS topic literals suppresses the whole file with one marker.
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelHardcodedTopicScanResult(path=path, flagged=False, findings=())

    findings: list[ModelHardcodedTopicFinding] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        for match in _TOPIC_PATTERN.finditer(line):
            # Strip the surrounding quotes to report the bare topic string.
            topic = match.group(0)[1:-1]
            findings.append(
                ModelHardcodedTopicFinding(
                    path=path,
                    line=lineno,
                    topic=topic,
                    context=line.strip(),
                )
            )
    return ModelHardcodedTopicScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerHardcodedTopicCompute:
    """COMPUTE handler: scan one source-text payload for hardcoded onex.* topics.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-hardcoded-topic-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"HardcodedTopicScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelHardcodedTopicScanInput]
    ) -> ModelHandlerOutput[ModelHardcodedTopicScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
