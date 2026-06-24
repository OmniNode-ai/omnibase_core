# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-internal-ip OMN-13569 reason="this validator's docstrings/regex name the RFC1918 + RFC5737 ranges it scans for; the IP literals are the subject, not config"
"""HandlerDocContentScanCompute — generated COMPUTE validator for doc-content traces.

GENERATED ARTIFACT (OMN-13569, G2). The scanning logic in ``scan_source`` is a
structured refactor of the seed produced by ``HandlerGenerationConsumer``
(``node_generation_consumer``, omnimarket), local-model-first through the real
delegation chain against the live model (``Qwen3.6-35B-A3B`` on the local-coder
backend at ``http://192.168.86.201:8000/v1/chat/completions``),  # onex-allow-internal-ip OMN-13569 provenance: the live generation backend endpoint
and accepted ONLY because it passed a deterministic acceptance corpus
(``node_generation_consumer.validator_corpora.corpus_doc_content_scan.DOC_CONTENT_SCAN_CORPUS``)
in the hardened sandbox on the FIRST attempt: it flagged every ``violation_fixture``
(6 base + 9 adversarial mutation) and produced zero findings on every
``clean_fixture`` (13, incl. 8 adversarial mutation). The corpus verdict — not the
LLM's self-report — was the acceptance authority (memory
``feedback_adversarial_receipts``). See ``GENERATION_PROVENANCE.md`` for the full
run; the raw generated ``handle(input_data)`` is committed verbatim in
``omnimarket/docs/evidence/OMN-13569/doc-content-scan.generation.json``.

The invariant — "a documentation file (``*.md`` / ``.mdx`` / ``.rst`` / ``.txt`` /
``.adoc``) must not carry local-environment traces or Linear ticket references,
except where exempt" — is the docs-facing union of CLAUDE.md Rule 6 (no hardcoded
LAN IPs / personal absolute paths) and the knowledge-base sanitizer (strip OMN ids
/ IPs / ``.201`` / private URLs / e-mail) that already runs on the public
knowledge-base repo.

Hand-hardening applied to the corpus-accepted seed (the seed is a SEED, not a
drop-in):

* Structured the raw ``handle(input_data)`` dict-return into the canonical
  ``line`` / ``column`` / ``violation_type`` / ``matched_text`` / ``context``
  finding shape (mirrors the sibling private-IP / hardcoded-topic validators), and
  emits at most one finding per (line, class) in a stable source order so the
  verdict is order-independent regardless of dispatch backend (§1A).
* Added the PATH-based ``OMN-<digits>`` exemptions the corpus (text-only) could not
  express: a file under ``onex_change_control/`` or ``contracts/`` keeps its ticket
  references (governance ledgers + contract fixtures legitimately cite OMN ids),
  but the local-environment rules (LAN IP / host shorthand / personal path / ssh /
  e-mail) still apply everywhere. This is a pure decision over the ``path`` LABEL
  string — the handler never opens the path.
* ``localhost`` / ``127.0.0.1`` are LEFT by decision (portable, non-identifying);
  the RFC5737 documentation ranges (``192.0.2.x`` / ``198.51.100.x`` /
  ``203.0.113.x``) and ``example.com`` are the canonical illustrative placeholders
  and are not flagged.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT (and
the path LABEL) carried on the envelope payload and performs no filesystem /
network / env I/O. Selecting the docs-only file set and loading file bytes is the
EFFECT boundary's job (``runtime_doc_content_scan``), never the handler's — that is
what preserves COMPUTE purity (§1A).
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.doc_content_scan.models import (
    EnumDocViolationType,
    ModelDocContentFinding,
    ModelDocContentScanInput,
    ModelDocContentScanResult,
)

__all__ = ["HandlerDocContentScanCompute", "scan_source"]

# Candidate IPv4 literal: four dotted 1-3 digit octets on a word boundary. The
# regex only *finds* candidates; RFC1918 membership (and RFC5737/loopback
# exclusion) is decided by octet parsing in ``_lan_ip_match`` so a doc-reserved
# 192.0.2.x address and the loopback 127.0.0.1 are correctly left clean.
_IPV4_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
)

# A ``.201`` / ``.200`` host shorthand referring to a host: a dot then exactly 201
# or 200 as a standalone token, NOT preceded by a digit or dot (so a decimal like
# ``0.200`` or a SemVer patch like ``v1.201.0`` is excluded) and NOT followed by a
# further dotted digit (so the third octet of an IP is not double-counted).
_HOST_SHORTHAND: Final[re.Pattern[str]] = re.compile(
    r"(?<![\d.])\.(?:201|200)\b(?!\.\d)"
)

# A personal absolute home path: /Users/<name>/ or /home/<name>/ — the portable
# $OMNI_HOME / ${ONEX_HOST} / Path.home() forms carry no leading /Users|/home root
# and so never match.
_PERSONAL_PATH: Final[re.Pattern[str]] = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+")

# An ssh invocation of the shape ``ssh <user>@<host>``.
_SSH_INVOCATION: Final[re.Pattern[str]] = re.compile(r"\bssh\s+\S+@\S+")

# A personal e-mail address at a real consumer mail domain. ``example.com`` is the
# reserved documentation domain and is excluded by construction (it is not in the
# domain alternation).
_PERSONAL_EMAIL: Final[re.Pattern[str]] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@"
    r"(?:gmail|yahoo|hotmail|outlook|icloud|protonmail|aol|mail|zoho|yandex|tutanota)"
    r"\.[A-Za-z]{2,}\b"
)

# A Linear ticket reference: OMN-<digits> as a standalone token (so OMNI_HOME /
# OMNINODE are not matched). Matches anywhere on the line — prose, parenthetical,
# heading, list item, link target, or embedded filename.
_TICKET_REFERENCE: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])OMN-\d+\b")

# Line-level escape hatch: a line carrying this exact marker is suppressed.
_SUPPRESSION_MARKER: Final[str] = "doc-content-ok"

# File-level escape hatch: a file whose content carries this exact marker anywhere
# is suppressed in full (for a doc whose subject IS these traces, e.g. this
# validator's own provenance or a runbook documenting the markers themselves).
# NOTE: this string is a SUPERSTRING of the line marker, so the file check must run
# before any line-marker check (the file marker also contains "doc-content-ok").
_FILE_SUPPRESSION_MARKER: Final[str] = "doc-content-file-ok"

# Path prefixes under which an ``OMN-<digits>`` ticket reference is EXEMPT: the
# governance ledger repo and contract-fixture trees legitimately cite ticket ids.
# The local-environment rules still apply under these paths. Matched as a path
# segment so a substring elsewhere does not accidentally exempt.
_TICKET_EXEMPT_SEGMENTS: Final[tuple[str, ...]] = ("onex_change_control", "contracts")


def _lan_ip_match(o1: int, o2: int, o3: int, o4: int) -> bool:
    """True iff these octets are an RFC1918 LAN IP (and not RFC5737/loopback).

    Pure octet logic mirroring the private-IP validator's ground truth:
      * 10/8         -> first octet 10
      * 172.16/12    -> first octet 172, second octet 16-31 (inclusive)
      * 192.168/16   -> first octet 192, second octet 168
    The RFC5737 documentation ranges (192.0.2/24, 198.51.100/24, 203.0.113/24) and
    loopback 127.0.0.1 are public/reserved-for-docs and are NOT LAN traces — they
    fall through to ``False`` because none match an RFC1918 block.
    """
    for octet in (o1, o2, o3, o4):
        if octet > 255:
            return False
    if o1 == 10:
        return True
    if o1 == 172 and 16 <= o2 <= 31:
        return True
    if o1 == 192 and o2 == 168:
        return True
    return False


def _path_is_ticket_exempt(path: str) -> bool:
    """True iff ``path`` lives under a ticket-reference-exempt tree.

    Pure string decision over the path LABEL — no filesystem access. Split on both
    separators so a forward-slash label and a posix path both resolve the same.
    """
    segments = path.replace("\\", "/").split("/")
    for exempt in _TICKET_EXEMPT_SEGMENTS:
        if exempt in segments:
            return True
    return False


def scan_source(content: str, path: str = "<input>") -> ModelDocContentScanResult:
    """Scan documentation ``content`` for local-env traces + ticket references.

    Pure and deterministic. A line containing ``doc-content-ok`` is skipped; a file
    containing ``doc-content-file-ok`` is suppressed entirely. ``OMN-<digits>``
    references are skipped when ``path`` is under ``onex_change_control/`` or
    ``contracts/`` (the local-environment rules still apply there). Findings are
    emitted in a stable order (line, then class order, then column) so the verdict
    is order-independent regardless of dispatch backend (§1A).
    """
    # File-level escape hatch first: it is a superstring of the line marker.
    if _FILE_SUPPRESSION_MARKER in content:
        return ModelDocContentScanResult(path=path, flagged=False, findings=())

    ticket_exempt = _path_is_ticket_exempt(path)
    findings: list[ModelDocContentFinding] = []

    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue

        # LAN IP — octet-parse each candidate; flag the first private one.
        for match in _IPV4_CANDIDATE.finditer(line):
            o1, o2, o3, o4 = (int(g) for g in match.groups())
            if _lan_ip_match(o1, o2, o3, o4):
                findings.append(
                    ModelDocContentFinding(
                        path=path,
                        line=lineno,
                        column=match.start() + 1,
                        violation_type=EnumDocViolationType.LAN_IP,
                        matched_text=match.group(),
                        context=line.strip(),
                    )
                )
                break

        # The remaining classes each contribute at most one finding per line.
        for pattern, violation_type in (
            (_HOST_SHORTHAND, EnumDocViolationType.HOST_SHORTHAND),
            (_PERSONAL_PATH, EnumDocViolationType.PERSONAL_PATH),
            (_SSH_INVOCATION, EnumDocViolationType.SSH_INVOCATION),
            (_PERSONAL_EMAIL, EnumDocViolationType.PERSONAL_EMAIL),
        ):
            class_match = pattern.search(line)
            if class_match is not None:
                findings.append(
                    ModelDocContentFinding(
                        path=path,
                        line=lineno,
                        column=class_match.start() + 1,
                        violation_type=violation_type,
                        matched_text=class_match.group(),
                        context=line.strip(),
                    )
                )

        # Ticket reference — exempt under governance/contract trees.
        if not ticket_exempt:
            ticket = _TICKET_REFERENCE.search(line)
            if ticket is not None:
                findings.append(
                    ModelDocContentFinding(
                        path=path,
                        line=lineno,
                        column=ticket.start() + 1,
                        violation_type=EnumDocViolationType.TICKET_REFERENCE,
                        matched_text=ticket.group(),
                        context=line.strip(),
                    )
                )

    findings.sort(key=lambda f: (f.line, f.violation_type.value, f.column))
    return ModelDocContentScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerDocContentScanCompute:
    """COMPUTE handler: scan one documentation payload for content traces + tickets.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns the
    verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-doc-content-scan-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"DocContentScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelDocContentScanInput]
    ) -> ModelHandlerOutput[ModelDocContentScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
