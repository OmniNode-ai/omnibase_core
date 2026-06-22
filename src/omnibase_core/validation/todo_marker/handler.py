# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-todo-marker OMN-13480 reason="this validator's docs/strings name the TODO/FIXME/HACK marker token as their SUBJECT; the tokens are not unfinished work"
"""HandlerTodoMarkerCompute — generated COMPUTE validator for unfinished-work markers.

GENERATED ARTIFACT (OMN-13480, G2 SEA-dogfood). The scanning logic in
``scan_source`` was produced by ``HandlerGenerationConsumer``
(``node_generation_consumer``, omnimarket), local-model-first through the real
delegation chain against the live model, and accepted ONLY because it passed a
deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_todo_marker.TODO_MARKER_CORPUS``)
in the hardened sandbox: it flagged every ``violation_fixture`` (2 base + 3
adversarial mutation) and produced zero findings on every ``clean_fixture``
(ordinary comment, marker-substring identifier, ``hackathon`` lowercase substring,
lowercase prose "to do"). The corpus verdict — not the LLM's self-report — was the
acceptance authority (memory ``feedback_adversarial_receipts``). See
``GENERATION_PROVENANCE.md`` for the full run.

The raw generated ``handle(input_data)`` (623 chars) is committed verbatim in the
provenance evidence
(``docs/evidence/2026-06-22-sea-dogfood-handler/todo-fixme-marker.generation.json``);
its core is the word-boundary scan ``re.compile(r"\\b(TODO|FIXME|HACK)\\b")`` over
each line — the EXACT pattern ``node_aislop_sweep._TODO_PATTERN`` already encodes
advisorily. This handler turns that advisory detection into a BLOCKING gate.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job (``runtime_todo_marker``),
never the handler's — that is what preserves COMPUTE purity (§1A).

The committed ``scan_source`` is a structured refactor of the generated logic: it
adds ``line`` / ``marker`` / ``context`` to each finding to match the canonical
finding shape, and adds line-level (``# onex-allow-todo-marker``) and file-level
(``# onex-allow-file-todo-marker``) escape hatches so ticket-referenced markers and
documentation-heavy source whose subject IS the marker token are not false-flagged.
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.todo_marker.models import (
    ModelTodoMarkerFinding,
    ModelTodoMarkerScanInput,
    ModelTodoMarkerScanResult,
)

__all__ = ["HandlerTodoMarkerCompute", "scan_source"]

# Whole-word work-item marker: only the standalone uppercase tokens, on word
# boundaries. ``\b`` on both sides is what makes the marker a substring of a
# larger identifier (``TODOLIST``, ``mastodon``, ``hackathon``) NOT match — the
# clean corpus mutations pin exactly that boundary behaviour. This is the SAME
# pattern node_aislop_sweep._TODO_PATTERN encodes (the hand-authored ground truth).
_MARKER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b(TODO|FIXME|HACK)\b")

# A line carrying this exact marker is suppressed (allowlisted) — the canonical
# line-level escape hatch for an approved, ticket-referenced unfinished-work note.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-todo-marker"

# A file whose content carries this exact marker anywhere is suppressed in full.
# File-level escape hatch for documentation-heavy source whose subject IS the
# marker token (e.g. this validator's own docs, the aislop sweep, the TODO-policy
# docs) — line markers there would pollute the rendered prose.
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-allow-file-todo-marker"


def scan_source(content: str, path: str = "<input>") -> ModelTodoMarkerScanResult:
    """Scan ``content`` line by line for agent-left unfinished-work markers.

    Pure and deterministic. A line containing the ``onex-allow-todo-marker``
    suppression marker is skipped; otherwise every whole-word TODO/FIXME/HACK
    token on the line is flagged. Findings are emitted in a stable order (line,
    then in-line marker order) so the verdict is order-independent regardless of
    dispatch backend (§1A).
    """
    findings: list[ModelTodoMarkerFinding] = []
    # File-level escape hatch: a documentation-heavy source whose subject IS the
    # marker token suppresses the whole file with one marker.
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelTodoMarkerScanResult(path=path, flagged=False, findings=())
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        for match in _MARKER_PATTERN.finditer(line):
            findings.append(
                ModelTodoMarkerFinding(
                    path=path,
                    line=lineno,
                    marker=match.group(1),
                    context=line.strip(),
                )
            )
    return ModelTodoMarkerScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerTodoMarkerCompute:
    """COMPUTE handler: scan one source-text payload for unfinished-work markers.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-todo-marker-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"TodoMarkerScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelTodoMarkerScanInput]
    ) -> ModelHandlerOutput[ModelTodoMarkerScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
