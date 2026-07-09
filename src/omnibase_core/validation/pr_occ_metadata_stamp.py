# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parser/renderer for canonical PR OCC metadata stamps (OMN-14188)."""

from __future__ import annotations

import re

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind
from omnibase_core.models.validation.model_pr_body_section import ModelPrBodySection
from omnibase_core.models.validation.model_pr_evidence_source import (
    ModelPrEvidenceSource,
)
from omnibase_core.models.validation.model_pr_occ_metadata_stamp import (
    ModelPrOccMetadataStamp,
)
from omnibase_core.models.validation.model_pr_receipt_gate_skip_token import (
    ModelPrReceiptGateSkipToken,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_EVIDENCE_TICKET_RE = re.compile(
    r"^Evidence-Ticket:\s*(OMN-\d+)\s*$",
    re.IGNORECASE,
)
_EVIDENCE_SOURCE_OCC_PR_RE = re.compile(
    r"^Evidence-Source:\s+OCC#(\d+)\s*$",
    re.IGNORECASE,
)
_EVIDENCE_SOURCE_SHA_RE = re.compile(
    r"^Evidence-Source:\s+([0-9a-f]{7,40})\s*$",
    re.IGNORECASE,
)
_EVIDENCE_LINE_RE = re.compile(
    r"^Evidence-(?:Ticket|Source):\s+\S",
    re.IGNORECASE,
)
_SKIP_TOKEN_RE = re.compile(
    r"\[skip-([a-zA-Z][a-zA-Z0-9_-]*):\s*([^\]<>]*)\]",
    re.IGNORECASE,
)
_ALLOWLIST_RE = re.compile(r"#\s*skip-token-allowed:\s*(\S+)", re.IGNORECASE)
_STAMP_HEADING_TITLES = frozenset(
    {
        "evidence",
        "occ evidence",
        "occ metadata",
        "receipt evidence",
    }
)


def parse_pr_occ_metadata_stamp(
    pr_body: str,
    *,
    repo: str = "",
    pr_number: int | None = None,
    head_sha: str | None = None,
) -> ModelPrOccMetadataStamp:
    """Parse a PR body into the canonical OCC metadata stamp model.

    The parser is intentionally lossless for body text. ``body_sections`` keeps
    every source byte in order, marking sections that contain the renderer-owned
    Evidence metadata so the renderer can replace only that owned block.
    """
    return ModelPrOccMetadataStamp(
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        evidence_source=_parse_evidence_source(pr_body),
        evidence_tickets=tuple(_parse_evidence_tickets(pr_body)),
        skip_tokens=tuple(_parse_skip_tokens(pr_body)),
        body_sections=tuple(_parse_body_sections(pr_body)),
    )


def render_pr_occ_metadata_stamp(stamp: ModelPrOccMetadataStamp) -> str:
    """Render ``stamp`` back to a PR body with one canonical Evidence block."""
    human_body = "".join(
        section.content
        for section in stamp.body_sections
        if not section.is_stamp_section
    )
    stamp_block = _render_stamp_block(stamp)
    if not stamp_block:
        return human_body
    if not human_body.strip():
        return stamp_block
    return f"{human_body.rstrip()}\n\n{stamp_block}"


def _parse_body_sections(pr_body: str) -> list[ModelPrBodySection]:
    sections: list[ModelPrBodySection] = []
    current_heading = None
    current_is_stamp = None
    current_lines: list[str] = []

    for line in pr_body.splitlines(keepends=True):
        line_heading = _heading_from_line(line)
        line_is_stamp = _is_stamp_line(line)
        if current_is_stamp is not None and not line.strip():
            line_is_stamp = current_is_stamp
        if current_is_stamp is not None and line_is_stamp is not current_is_stamp:
            sections.append(
                _section_from_lines(
                    current_heading,
                    current_lines,
                    is_stamp_section=current_is_stamp,
                )
            )
            current_lines = []
            current_heading = None
        if not current_lines:
            current_heading = line_heading
            current_is_stamp = line_is_stamp
        elif line_heading is not None and current_heading is None:
            if not "".join(current_lines).strip():
                current_heading = line_heading
        current_lines.append(line)

    if current_lines or not sections:
        sections.append(
            _section_from_lines(
                current_heading,
                current_lines,
                is_stamp_section=bool(current_is_stamp),
            )
        )
    return sections


def _section_from_lines(
    heading: str | None,
    lines: list[str],
    *,
    is_stamp_section: bool,
) -> ModelPrBodySection:
    content = "".join(lines)
    return ModelPrBodySection(
        heading=heading,
        content=content,
        is_stamp_section=is_stamp_section,
    )


def _heading_from_line(line: str) -> str | None:
    if match := _HEADING_RE.match(line.rstrip("\r\n")):
        return match.group(2).strip()
    return None


def _is_stamp_line(line: str) -> bool:
    if (
        _EVIDENCE_LINE_RE.match(line) is not None
        or _SKIP_TOKEN_RE.search(line) is not None
        or _ALLOWLIST_RE.search(line) is not None
    ):
        return True
    heading = _heading_from_line(line)
    if heading is not None:
        return heading.lower() in _STAMP_HEADING_TITLES
    return False


def _parse_evidence_tickets(pr_body: str) -> list[str]:
    tickets: list[str] = []
    for line in pr_body.splitlines():
        if match := _EVIDENCE_TICKET_RE.fullmatch(line.strip()):
            tickets.append(match.group(1))
    return tickets


def _parse_evidence_source(pr_body: str) -> ModelPrEvidenceSource | None:
    for line in pr_body.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("evidence-source:"):
            continue
        if match := _EVIDENCE_SOURCE_OCC_PR_RE.fullmatch(stripped):
            return ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.OCC_PR,
                occ_pr_number=int(match.group(1)),
            )
        if match := _EVIDENCE_SOURCE_SHA_RE.fullmatch(stripped):
            return ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.COMMIT_SHA,
                commit_sha=match.group(1),
            )
        return None
    return None


def _parse_skip_tokens(pr_body: str) -> list[ModelPrReceiptGateSkipToken]:
    parsed: list[ModelPrReceiptGateSkipToken] = []
    for line in pr_body.splitlines():
        if allowlist_match := _ALLOWLIST_RE.search(line):
            parsed = _bind_allowlist_to_latest_token(parsed, allowlist_match.group(1))
            continue
        for match in _SKIP_TOKEN_RE.finditer(line):
            parsed.append(
                ModelPrReceiptGateSkipToken(
                    gate_name=match.group(1),
                    reason=match.group(2).strip(),
                )
            )
    return parsed


def _bind_allowlist_to_latest_token(
    tokens: list[ModelPrReceiptGateSkipToken],
    allowlist_receipt_id: str,
) -> list[ModelPrReceiptGateSkipToken]:
    if not tokens:
        return tokens
    rebound = list(tokens)
    latest = rebound[-1]
    rebound[-1] = latest.model_copy(
        update={"allowlist_receipt_id": allowlist_receipt_id}
    )
    return rebound


def _render_stamp_block(stamp: ModelPrOccMetadataStamp) -> str:
    lines: list[str] = []
    lines.extend(f"Evidence-Ticket: {ticket}" for ticket in stamp.evidence_tickets)
    if stamp.evidence_source is not None:
        lines.append(f"Evidence-Source: {stamp.evidence_source.render_token()}")
    for token in stamp.skip_tokens:
        lines.append(token.render_token())
        if token.allowlist_receipt_id is not None:
            lines.append(f"# skip-token-allowed: {token.allowlist_receipt_id}")
    return "\n".join(lines) + ("\n" if lines else "")


__all__ = ["parse_pr_occ_metadata_stamp", "render_pr_occ_metadata_stamp"]
