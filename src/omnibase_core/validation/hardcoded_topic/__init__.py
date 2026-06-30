# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Hardcoded-topic-string validator — canonical COMPUTE node (OMN-13294, G2 SEA-dogfood).

This package is the "agent lands what SEA generated" step: a generated mechanical
scanner for hardcoded ONEX ``onex.<a>.<b>.<c>`` event-topic string literals,
produced by the canonical generator ``HandlerGenerationConsumer``
(``node_generation_consumer``, omnimarket) against the live model and accepted
ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_hardcoded_topic.HARDCODED_TOPIC_CORPUS``)
in the hardened sandbox — the corpus verdict, not the LLM, is the acceptance
authority (OMN-13289). See ``GENERATION_PROVENANCE.md``.

Architecture (§1A — validator = COMPUTE node over a swappable bus), mirroring the
G1 local-paths canary and the G2 private-IP / unfinished-work-marker validators:

* ``ModelHardcodedTopicScanInput`` / ``ModelHardcodedTopicScanResult`` — typed
  envelope payload + verdict (``models``).
* ``HandlerHardcodedTopicCompute`` — a pure, deterministic COMPUTE handler
  implementing ``ProtocolMessageHandler``; it reads the file *content text* from
  the envelope payload and returns findings as ``ModelHandlerOutput.result``. It
  performs NO I/O — that is what preserves COMPUTE purity.
* ``runtime_hardcoded_topic`` — the runner: the EFFECT boundary that loads the
  staged file set (the I/O) and dispatches each file as a command envelope to the
  COMPUTE handler **over the event bus** — in-memory backend at pre-commit time,
  Kafka in CI. Same handler; only the backend (config) changes.

Invariant: a quoted ``onex.<a>.<b>.<c>`` topic literal in source is a
contract-drift bug — topics must be declared in ``contract.yaml`` and resolved
through it, never pasted as a string literal in a handler. This turns the
ADVISORY ``node_aislop_sweep`` ``_HARDCODED_TOPIC_PATTERN`` ground truth into a
BLOCKING gate.
"""

from __future__ import annotations

from omnibase_core.validation.hardcoded_topic.handler import (
    HandlerHardcodedTopicCompute,
    scan_source,
)
from omnibase_core.validation.hardcoded_topic.models import (
    ModelHardcodedTopicFinding,
    ModelHardcodedTopicScanInput,
    ModelHardcodedTopicScanResult,
)

__all__ = [
    "HandlerHardcodedTopicCompute",
    "ModelHardcodedTopicFinding",
    "ModelHardcodedTopicScanInput",
    "ModelHardcodedTopicScanResult",
    "scan_source",
]
