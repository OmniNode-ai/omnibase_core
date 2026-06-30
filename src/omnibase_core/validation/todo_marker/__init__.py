# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-todo-marker OMN-13480 reason="this validator's docs/strings name the TODO/FIXME/HACK marker token as their SUBJECT; the tokens are not unfinished work"
"""Unfinished-work-marker validator — canonical COMPUTE node (OMN-13480, G2 SEA-dogfood).

This package is the "agent lands what SEA generated" step: a generated mechanical
scanner for agent-left TODO/FIXME/HACK markers, produced by the canonical generator
``HandlerGenerationConsumer`` (``node_generation_consumer``, omnimarket) against the
live model and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_todo_marker.TODO_MARKER_CORPUS``)
in the hardened sandbox — the corpus verdict, not the LLM, is the acceptance
authority (OMN-13289). See ``GENERATION_PROVENANCE.md``.

Architecture (§1A — validator = COMPUTE node over a swappable bus), mirroring the
G1 local-paths canary and the G2 private-IP validator:

* ``ModelTodoMarkerScanInput`` / ``ModelTodoMarkerScanResult`` — typed envelope
  payload + verdict (``models``).
* ``HandlerTodoMarkerCompute`` — a pure, deterministic COMPUTE handler
  implementing ``ProtocolMessageHandler``; it reads the file *content text* from
  the envelope payload and returns findings as ``ModelHandlerOutput.result``. It
  performs NO I/O — that is what preserves COMPUTE purity.
* ``runtime_todo_marker`` — the runner: the EFFECT boundary that loads the staged
  file set (the I/O) and dispatches each file as a command envelope to the
  COMPUTE handler **over the event bus** — in-memory backend at pre-commit time,
  Kafka in CI. Same handler; only the backend (config) changes.
"""

from __future__ import annotations

from omnibase_core.validation.todo_marker.handler import HandlerTodoMarkerCompute
from omnibase_core.validation.todo_marker.models import (
    ModelTodoMarkerFinding,
    ModelTodoMarkerScanInput,
    ModelTodoMarkerScanResult,
)

__all__ = [
    "HandlerTodoMarkerCompute",
    "ModelTodoMarkerFinding",
    "ModelTodoMarkerScanInput",
    "ModelTodoMarkerScanResult",
]
