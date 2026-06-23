# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerPinHygieneCompute — generated COMPUTE validator for sibling pin hygiene.

GENERATED ARTIFACT (OMN-13509). The sibling-detection + git-pin-syntax +
ancestry-verdict scanning regexes in ``scan_source`` were produced by
``node_generation_consumer`` (omnimarket), local-model-first through the real
delegation chain (model ``Qwen3.6-35B-A3B`` on the local-coder backend at
``http://192.168.86.201:8000/v1/chat/completions``),  # onex-allow-internal-ip OMN-13509 provenance: the live generation backend endpoint
and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_pin_hygiene``) in the
hardened sandbox: it flagged every ``violation_fixture`` (3 base + 4 adversarial
mutation: PEP-508 ``@rev`` form, uv.lock ``?rev=`` form, diverged ``branch=main``,
and an ``unknown`` fail-closed pin) and produced zero findings on every
``clean_fixture`` (ancestor pin in each syntax, a non-sibling git pin, a
version-range pin with no git rev). The corpus verdict — not the LLM's
self-report — was the acceptance authority (memory ``feedback_adversarial_receipts``).
See ``GENERATION_PROVENANCE.md`` for the full run.

Hand-hardening applied to the corpus-accepted seed (the seed is a SEED, not
drop-in — it hallucinated a module path and carried a fail-OPEN hole):

* The seed SKIPPED a sibling git pin that carried no ``# pin-ancestry:``
  annotation (``if not ancestry_match: continue``). That is fail-OPEN: an
  unannotated sibling git pin would pass the gate. This gate FAILS CLOSED — a
  sibling git pin with no resolved-ancestry annotation is treated as
  ``unknown`` and FLAGGED. (The EFFECT runner always annotates, so in practice a
  missing annotation means the runner could not resolve ancestry — exactly the
  fail-closed case.)
* Added the ``onex-allow-pin-hygiene`` per-line suppression marker.
* Findings are emitted in source order (line number) so the verdict is
  order-independent regardless of dispatch backend.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env / git
I/O. Resolving each pin's git ancestry (``git merge-base --is-ancestor <rev>
<sibling-dev-head>``) and annotating the loaded text is the EFFECT boundary's job
(``runtime_pin_hygiene``), never the handler's — that is what preserves COMPUTE
purity.

The invariant — "a sibling dependency pin (``omnibase-core`` / ``omnibase-spi`` /
``omnibase-compat`` git rev or ``branch=`` in ``pyproject.toml`` / ``uv.lock``)
whose pinned commit is NOT an ancestor of that sibling's ``dev`` HEAD is a
divergence bug" — turns the #2071 / OMN-13507 recurrence into a BLOCKING gate.
The ``onex-allow-pin-hygiene`` suppression marker is the per-line escape hatch.
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.pin_hygiene.models import (
    ModelPinHygieneFinding,
    ModelPinHygieneScanInput,
    ModelPinHygieneScanResult,
)

__all__ = ["HandlerPinHygieneCompute", "scan_source"]

# A line carrying this exact marker is suppressed (allowlisted). The escape hatch
# exists for the corpus / test-fixture sources whose SUBJECT is the diverged-pin
# pattern the scanner must flag, and for genuinely-approved exceptions.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-pin-hygiene"

# The verdict an annotated-clean pin carries; every other annotation (orphan,
# unknown) and a MISSING annotation on a sibling git pin is a violation (fail
# closed). Lower-cased before comparison.
_CLEAN_VERDICT: Final[str] = "ancestor"

# === GENERATED SCANNING REGEXES (OMN-13509) — preserved from the corpus-accepted
# artifact (verbatim where correct). Each pattern recognises one pin syntax or the
# ancestry annotation. ===

# The three guarded sibling distributions, in both the hyphenated distribution
# name (pyproject/lock package key) and the underscore repo name (inside the git
# URL). Only these are in scope.
_SIBLINGS: Final[tuple[str, ...]] = (
    "omnibase-core",
    "omnibase-spi",
    "omnibase-compat",
    "omnibase_core",
    "omnibase_spi",
    "omnibase_compat",
)

# Sibling name appearing as a delimited token on the line (not a substring of a
# longer identifier). HARDENED beyond the generated seed: the seed's delimiter set
# did NOT include the `/` prefix and `.` suffix, so it MISSED the sibling name when
# it appears only inside a git URL path — e.g. the uv.lock `[[package]]` stanza
# `source = { git = ".../omnibase_compat.git?branch=main#<sha>" }`, where the
# package key `name = "omnibase-compat"` is on a SEPARATE line. That is the literal
# #2071 / OMN-13507 form (a uv.lock pin), so missing it would defeat the gate's
# core purpose. The `/` prefix and `.`/`@` suffix catch the URL-embedded repo name.
_PATTERN_SIBLING: Final[re.Pattern[str]] = re.compile(
    rf'(?:^|\s|"|,|;|/)({"|".join(_SIBLINGS)})(?:\s|,|;|"|\[|@|\.|$)',
    re.IGNORECASE,
)

# (a) pyproject [tool.uv.sources] form: rev = "<sha>".
_PATTERN_REV: Final[re.Pattern[str]] = re.compile(
    r'rev\s*=\s*["\']([a-fA-F0-9]+)["\']',
    re.IGNORECASE,
)

# (b) PEP-508 form: @<sha> after a git+https URL.
_PATTERN_PEP508: Final[re.Pattern[str]] = re.compile(
    r"""git\+https://.*?@([a-fA-F0-9]{7,40})(?=#|$|["'])""",
)

# (c) uv.lock form: ?rev=<sha>.
_PATTERN_UVLOCK: Final[re.Pattern[str]] = re.compile(
    r"\?rev=([a-fA-F0-9]{7,40})",
)

# git branch pin, in both the TOML form `branch = "<name>"` and the uv.lock URL
# form `?branch=<name>`. The uv.lock `?branch=` form is a HARDENING beyond the
# corpus-accepted seed (the corpus covered the TOML `branch =` form; uv.lock
# expresses a branch pin as `...omnibase_compat.git?branch=main`, which the seed
# would have missed — exactly the silent-passthrough this gate must not have).
_PATTERN_BRANCH: Final[re.Pattern[str]] = re.compile(
    r'branch\s*=\s*["\']([^"\']+)["\']|\?branch=([A-Za-z0-9._/\-]+)',
    re.IGNORECASE,
)

# The resolved-ancestry annotation the EFFECT runner injects on each pin line.
_PATTERN_ANCESTRY: Final[re.Pattern[str]] = re.compile(
    r"#\s*pin-ancestry:\s*(\w+)",
)


def _pin_type(line: str) -> str:
    """Classify a sibling git pin line by its syntax for the finding label."""
    if _PATTERN_REV.search(line):
        return "rev"
    if _PATTERN_PEP508.search(line):
        return "pep-508"
    if _PATTERN_UVLOCK.search(line):
        return "uv-lock-rev"
    if _PATTERN_BRANCH.search(line):
        return "branch"
    return "unknown"


def scan_source(content: str, path: str = "<input>") -> ModelPinHygieneScanResult:
    """Scan ``content`` line by line for sibling git pins that are NOT ancestors.

    Pure and deterministic. A line carrying the ``onex-allow-pin-hygiene``
    suppression marker is skipped. For every other line: if it names a guarded
    sibling AND carries a git rev/branch pin, its resolved-ancestry annotation
    (``# pin-ancestry:`` injected by the EFFECT runner) is read. The line is
    flagged when the verdict is anything other than ``ancestor`` — ``orphan``
    (diverged / off-dev-line) and ``unknown`` (unresolved) both fail. A sibling
    git pin that carries NO annotation is treated as ``unknown`` and FLAGGED
    (fail closed). Findings are emitted in source order (line number) so the
    verdict is order-independent regardless of dispatch backend.
    """
    findings: list[ModelPinHygieneFinding] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        stripped = line.strip()
        if not stripped:
            continue

        sibling_match = _PATTERN_SIBLING.search(line)
        if sibling_match is None:
            continue
        sibling = sibling_match.group(1)

        is_git_pin = (
            _PATTERN_REV.search(line) is not None
            or _PATTERN_PEP508.search(line) is not None
            or _PATTERN_UVLOCK.search(line) is not None
            or _PATTERN_BRANCH.search(line) is not None
        )
        if not is_git_pin:
            # A sibling pinned by a published version range (no git rev) is not a
            # git pin — out of scope, clean.
            continue

        ancestry_match = _PATTERN_ANCESTRY.search(line)
        # Hardened: a missing annotation on a sibling git pin is fail-CLOSED
        # (unknown), NOT a silent skip (the generated seed skipped it — fail open).
        verdict = (
            ancestry_match.group(1).strip().lower()
            if ancestry_match is not None
            else "unknown"
        )
        if verdict == _CLEAN_VERDICT:
            continue

        findings.append(
            ModelPinHygieneFinding(
                path=path,
                line=lineno,
                sibling=sibling,
                pin_type=_pin_type(line),
                verdict=verdict,
                matched_text=stripped,
            )
        )

    findings.sort(key=lambda f: (f.line, f.sibling))
    return ModelPinHygieneScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerPinHygieneCompute:
    """COMPUTE handler: scan one dependency-pin payload for non-ancestor sibling pins.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-pin-hygiene-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"PinHygieneScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelPinHygieneScanInput]
    ) -> ModelHandlerOutput[ModelPinHygieneScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
