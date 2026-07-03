# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerNoFakedBoundaryCompute — generated COMPUTE validator for faked boundaries.

GENERATED ARTIFACT (OMN-13497). The four scanning regexes in ``scan_source`` were
produced by ``node_generation_consumer`` (omnimarket), local-model-first through
the real delegation chain (model ``Qwen3.6-35B-A3B`` on the local-coder backend at
``http://192.168.86.201:8000/v1/chat/completions``),  # onex-allow-internal-ip OMN-13497 provenance: the live generation backend endpoint
and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_no_faked_boundary``) in the
hardened sandbox: it flagged every ``violation_fixture`` (4 base + 4 adversarial
mutation) and produced zero findings on every ``clean_fixture`` (recorded-from-real
replay completion, real ``RoutingResolvedJudgeInferenceAdapter`` usage, real
``EventBusInmemory`` usage, external Slack/boto3 mocks, recorded literal whose
prose merely contains the word 'prompt'). The corpus verdict — not the LLM's
self-report — was the acceptance authority (memory ``feedback_adversarial_receipts``).
See ``GENERATION_PROVENANCE.md`` for the full run.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job (``runtime_no_faked_boundary``),
never the handler's — that is what preserves COMPUTE purity.

The invariant — "a hand-written class/object standing in for the platform's OWN
inference / routing / dispatch boundary (the inference bridge, model router,
routing-contract resolution, registry, or dispatch surface) that returns canned /
prompt-echoed output, or a ``patch("httpx.Client")`` / ``MagicMock`` substituting
that egress inside a real-dispatch test, is a FAKE of our architecture" — turns
the ``feedback_real_dispatch_path_tests`` failure ("handler-isolation tests pass
while live fails") into a BLOCKING gate.

Suppression / exemption (OMN-13500/13502):

* ``onex-allow-faked-boundary`` — per-LINE marker; the annotated line is skipped.
* ``onex-allow-file-faked-boundary`` — FILE-level marker; a file carrying it
  anywhere is skipped whole. Reserved for sources whose SUBJECT *is* the fake
  pattern (this detector's own docstring, and the acceptance-corpus test), which
  must quote the banned idioms verbatim. This module itself carries the marker
  below for exactly that reason: onex-allow-file-faked-boundary OMN-13497
  reason="detector source documents verbatim the patterns it bans".
* Canonical recorded-replay seam — a ``patch("httpx.Client")`` /
  ``patch("httpx.AsyncClient")`` that INJECTS a
  ``RecordedReplayInferenceTransport`` (OMN-13499) as the replacement is the
  canonical golden-chain seam, NOT a fake: live routing / model-selection /
  request construction still run, only recorded bytes are replayed, and the
  transport fails closed on route/hash drift. Such a patch is exempt from
  ``patch_httpx_egress``; a bare ``patch("httpx.Client") as mock`` (which then
  hand-sets canned bytes) or one injecting a ``MagicMock`` still flags.
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.no_faked_boundary.models import (
    ModelNoFakedBoundaryFinding,
    ModelNoFakedBoundaryScanInput,
    ModelNoFakedBoundaryScanResult,
)

__all__ = ["HandlerNoFakedBoundaryCompute", "scan_source"]

# A line carrying this exact marker is suppressed (allowlisted). The escape hatch
# exists for the corpus / test-fixture sources whose SUBJECT is the fake pattern
# the scanner must flag, and for genuinely-approved boundary doubles.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-faked-boundary"

# A file carrying this marker ANYWHERE is skipped whole. Reserved for sources
# whose subject IS the fake pattern (this detector's own docstring; the
# acceptance-corpus test). Distinct substring from _SUPPRESSION_MARKER — the
# per-line "onex-allow-faked-boundary" is NOT a substring of this token.
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-allow-file-faked-boundary"

# The canonical recorded-from-real replay transport (OMN-13499). A ``patch`` of
# the httpx egress that injects THIS as the replacement is the canonical
# golden-chain seam (live routing/selection/request construction still run; only
# recorded bytes are replayed and the transport fails closed on drift), so it is
# NOT a boundary fake. See OMN-13500/13502.
_CANONICAL_REPLAY_TRANSPORT: Final[str] = "RecordedReplayInferenceTransport"

# Names bound to a RecordedReplayInferenceTransport(...) construction anywhere in
# the file (e.g. ``transport = RecordedReplayInferenceTransport([fixture])``).
_REPLAY_BINDING: Final[re.Pattern[str]] = re.compile(
    r"(\w+)\s*=\s*" + _CANONICAL_REPLAY_TRANSPORT + r"\s*\(",
)

# A ``patch("httpx.Client"|"httpx.AsyncClient", <replacement>)`` that injects a
# replacement object (positional ``new`` or ``new=``/``return_value=`` keyword),
# capturing the injected NAME. A bare ``patch("httpx.Client") as mock`` (no
# injected replacement — the mock is captured to hand-set canned bytes) does NOT
# match here and therefore still flags.
_PATCH_INJECTED: Final[re.Pattern[str]] = re.compile(
    r"""patch\s*\(\s*["']httpx\.(?:Client|AsyncClient)["']\s*,\s*"""
    r"""(?:(?:new|return_value)\s*=\s*)?([A-Za-z_]\w*)""",
    re.IGNORECASE,
)

# === GENERATED SCANNING REGEXES (OMN-13497) — preserved verbatim from the
# corpus-accepted artifact. Each pattern is one fake-boundary signature. ===

# 1. A Fake/Stub/Mock class subclassing one of the platform's own boundary
#    protocols (*InferenceAdapter / *Bridge / *Router / *RoutingResolver /
#    *Dispatch*). A generic *Registry / *Mixin base (e.g. a service-registry
#    test harness) is NOT this boundary and is deliberately excluded — the
#    corpus pins that as a clean case (OMN-13497 shadow-run FP fix).
_PATTERN_CLASS: Final[re.Pattern[str]] = re.compile(
    r"class\s+\w*(?:Fake|Stub|Mock)\w*\s*\(.*?"
    r"(?:InferenceAdapter|Bridge|Router|RoutingResolver|Dispatch)",
    re.DOTALL,
)

# 2. Patching the real HTTP egress that backs inference.
_PATTERN_PATCH: Final[re.Pattern[str]] = re.compile(
    r"""patch\s*\(\s*["']httpx\.(?:Client|AsyncClient)["']""",
    re.IGNORECASE,
)

# 3. A MagicMock/AsyncMock assigned to an inference/bridge/router/dispatch target.
_PATTERN_MOCK_ASSIGNMENT: Final[re.Pattern[str]] = re.compile(
    r"(?:inference|bridge|router|dispatch)\w*\s*=\s*(?:MagicMock|AsyncMock)\(",
    re.IGNORECASE,
)

# 4a. completion=prompt (bare prompt identifier echo).
_PATTERN_COMPLETION_BARE: Final[re.Pattern[str]] = re.compile(
    r"completion\s*=\s*prompt\b",
    re.IGNORECASE,
)

# 4b. completion=f"...{prompt}..." (f-string interpolating the prompt variable).
_PATTERN_COMPLETION_FSTRING: Final[re.Pattern[str]] = re.compile(
    r"""completion\s*=\s*f["'].*?\{prompt\}.*?["']""",
    re.DOTALL | re.IGNORECASE,
)


def _patch_injects_canonical_replay(line: str, replay_names: set[str]) -> bool:
    """True iff ``line`` patches the httpx egress with the canonical replay transport.

    The canonical golden-chain seam is ``patch("httpx.Client", return_value=x)``
    (or positional ``new``) where ``x`` is a ``RecordedReplayInferenceTransport``.
    A bare ``patch("httpx.Client") as mock`` or one injecting a ``MagicMock`` does
    NOT match and is therefore still flagged as a boundary fake.
    """
    match = _PATCH_INJECTED.search(line)
    return match is not None and match.group(1) in replay_names


def scan_source(content: str, path: str = "<input>") -> ModelNoFakedBoundaryScanResult:
    """Scan ``content`` line by line for fakes of an inference/routing/dispatch boundary.

    Pure and deterministic. A file carrying the ``onex-allow-file-faked-boundary``
    marker is skipped whole; a line carrying the ``onex-allow-faked-boundary``
    marker is skipped; a ``patch`` that injects the canonical
    ``RecordedReplayInferenceTransport`` is exempt from ``patch_httpx_egress``.
    Otherwise each of the generated fake-boundary signatures is matched. Findings
    are emitted in source order (line number) so the verdict is order-independent
    regardless of dispatch backend.
    """
    # File-level escape hatch: the whole file is exempt (subject IS the pattern).
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelNoFakedBoundaryScanResult(path=path, flagged=False, findings=())

    # Names bound to the canonical recorded-replay transport anywhere in the file,
    # plus the class name itself (for inline ``return_value=Recorded...([f])``).
    replay_names: set[str] = set(_REPLAY_BINDING.findall(content))
    replay_names.add(_CANONICAL_REPLAY_TRANSPORT)

    findings: list[ModelNoFakedBoundaryFinding] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        stripped = line.strip()
        if not stripped:
            continue

        if _PATTERN_CLASS.search(line):
            findings.append(
                ModelNoFakedBoundaryFinding(
                    path=path,
                    line=lineno,
                    pattern="class_subclassing_boundary",
                    matched_text=stripped,
                )
            )
        if _PATTERN_PATCH.search(line) and not _patch_injects_canonical_replay(
            line, replay_names
        ):
            findings.append(
                ModelNoFakedBoundaryFinding(
                    path=path,
                    line=lineno,
                    pattern="patch_httpx_egress",
                    matched_text=stripped,
                )
            )
        if _PATTERN_MOCK_ASSIGNMENT.search(line):
            findings.append(
                ModelNoFakedBoundaryFinding(
                    path=path,
                    line=lineno,
                    pattern="mock_assigned_to_boundary",
                    matched_text=stripped,
                )
            )
        if _PATTERN_COMPLETION_BARE.search(line):
            findings.append(
                ModelNoFakedBoundaryFinding(
                    path=path,
                    line=lineno,
                    pattern="completion_echoes_prompt_var",
                    matched_text=stripped,
                )
            )
        elif _PATTERN_COMPLETION_FSTRING.search(line):
            findings.append(
                ModelNoFakedBoundaryFinding(
                    path=path,
                    line=lineno,
                    pattern="completion_fstring_interpolates_prompt",
                    matched_text=stripped,
                )
            )

    findings.sort(key=lambda f: (f.line, f.pattern))
    return ModelNoFakedBoundaryScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerNoFakedBoundaryCompute:
    """COMPUTE handler: scan one source-text payload for faked boundaries.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-no-faked-boundary-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"NoFakedBoundaryScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelNoFakedBoundaryScanInput]
    ) -> ModelHandlerOutput[ModelNoFakedBoundaryScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
