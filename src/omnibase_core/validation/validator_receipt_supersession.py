# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Supersession-chain resolution for DoD receipts (OMN-13888, scope item 3).

A receipt key ``(<TICKET>, <EVIDENCE_ITEM>, <CHECK_TYPE>)`` maps to a base file::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.yaml

plus an append-only chain of net-new correction records::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.supersede.<SUFFIX>.yaml

A tombstone record (``tombstone: true``, no replacement) invalidates the key; a
replacement record re-binds the key to a new receipt embedded in the record.
When no supersession file exists, the key resolves to its base receipt file.
No merged file is ever edited — corrections are always net-new files.

Two resolution tiers (OMN-16432):

1. **Target-aware.** When the caller supplies ``current_pr_number``, a single
   shared ``evidence_item_id`` may legitimately be re-bound to *several*
   different downstream consumer PRs by separate supersession records (e.g.
   an ``occ-self-bind-pr-<N>`` anchor rebound once per consumer). The record
   whose ``replacement.pr_number`` matches ``current_pr_number`` — or a
   tombstone, which invalidates the key for everyone — wins, using the
   chronologically latest (``created_at``) applicable record. This makes
   resolution correct regardless of what convention a record's filename
   suffix follows.
2. **Legacy fallback.** Untouched from the original OMN-13888 design: the
   record with the numerically highest ``NNNN`` filename suffix is
   authoritative. This is the sole path when no candidate explicitly targets
   ``current_pr_number`` (including when the caller passes no PR context at
   all), so existing single-consumer chains — the overwhelming majority, and
   the only shape that predates per-target binding — resolve exactly as
   before. Non-numeric suffixes never participate in this tiebreak, matching
   pre-OMN-16432 behavior.

This module keeps the path-local O(1) glob the receipt tree was built for; it
does not scan a global supersessions directory, and chain length for a single
key is always small (this is not a global scan).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_receipt_supersession import (
    ModelReceiptSupersession,
)

# Suffix is everything between ".supersede." and ".yaml" — deliberately not
# digit-only. A prior digit-only pattern silently dropped non-numeric-suffix
# files (e.g. "command.supersede.2010-head.yaml") from consideration with no
# error; widening this keeps every real record visible to resolution below.
_SUPERSEDE_SUFFIX_RE = re.compile(r"\.supersede\.([^./]+)\.yaml$")


@dataclass(frozen=True)
class SupersessionResolution:
    """Outcome of resolving a receipt key's supersession chain.

    Exactly one of ``receipt``, ``tombstoned``, or ``error`` is meaningful:

    - ``receipt`` set → the key is re-bound to this replacement receipt.
    - ``tombstoned`` True → the key is deliberately invalidated (no active
      receipt); the caller must treat it as MISSING / non-satisfied.
    - ``error`` set → the authoritative supersession record is
      unreadable/invalid; the caller must fail closed.

    ``source_path`` names the record used, for operator-facing messages.
    """

    receipt: ModelDodReceipt | None
    tombstoned: bool
    error: str | None
    source_path: Path


def _load_supersede_record(
    path: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
) -> tuple[ModelReceiptSupersession | None, str | None]:
    """Load, parse, and key-validate one supersession record.

    Returns ``(record, None)`` on success or ``(None, error_message)`` on any
    read/parse/key-mismatch failure.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except (yaml.YAMLError, OSError) as exc:
        return None, f"supersession record {path} is unreadable: {exc}"

    try:
        record = ModelReceiptSupersession.model_validate(raw)
    except ValidationError as exc:
        return None, f"supersession record {path} is invalid: {exc}"

    if (record.ticket_id, record.evidence_item_id, record.check_type) != (
        ticket_id,
        evidence_item_id,
        check_type,
    ):
        return None, (
            f"supersession record {path} declares key "
            f"({record.ticket_id}, {record.evidence_item_id}, "
            f"{record.check_type}) but is filed under "
            f"({ticket_id}, {evidence_item_id}, {check_type})"
        )
    return record, None


def _resolution_from_record(
    record: ModelReceiptSupersession, path: Path
) -> SupersessionResolution:
    if record.tombstone:
        return SupersessionResolution(
            receipt=None, tombstoned=True, error=None, source_path=path
        )
    return SupersessionResolution(
        receipt=record.replacement, tombstoned=False, error=None, source_path=path
    )


def resolve_supersession(
    receipts_dir: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
    current_pr_number: int | None = None,
) -> SupersessionResolution | None:
    """Resolve the active receipt for a key from its supersession chain.

    ``current_pr_number``, when supplied, scopes resolution to the record
    that explicitly targets that consumer PR (see module docstring, tier 1).
    Omitting it reproduces the original numeric-highest-suffix behavior
    exactly (tier 2) — every existing call site that has not been updated to
    pass PR context keeps behaving as it always has.

    Returns ``None`` when no supersession file exists for the key — the caller
    then proceeds with the base receipt file exactly as before (backward
    compatible). Otherwise returns a :class:`SupersessionResolution` describing
    the re-bind, the tombstone, or a load error from the authoritative record.
    """
    key_dir = receipts_dir / ticket_id / evidence_item_id
    if not key_dir.is_dir():
        return None

    candidates: list[tuple[str, Path]] = []
    for candidate in key_dir.glob(f"{check_type}.supersede.*.yaml"):
        match = _SUPERSEDE_SUFFIX_RE.search(candidate.name)
        if match is not None:
            candidates.append((match.group(1), candidate))
    if not candidates:
        return None

    # Load every candidate up front. This chain is already scoped to a single
    # receipt key (never a global scan) so it stays bounded by chain length —
    # in practice 1-5 files even for a heavily-corrected key.
    loaded: list[tuple[str, Path, ModelReceiptSupersession | None, str | None]] = []
    for suffix, path in candidates:
        record, err = _load_supersede_record(
            path, ticket_id, evidence_item_id, check_type
        )
        loaded.append((suffix, path, record, err))

    numeric = sorted(
        (item for item in loaded if item[0].isdigit()),
        key=lambda item: int(item[0]),
    )

    def _legacy_winner() -> SupersessionResolution | None:
        """Tier 2: numerically-highest suffix wins (pre-OMN-16432 behavior)."""
        if not numeric:
            return None
        _, path, record, err = numeric[-1]
        if record is None:
            return SupersessionResolution(
                receipt=None, tombstoned=False, error=err, source_path=path
            )
        return _resolution_from_record(record, path)

    if current_pr_number is None:
        return _legacy_winner()

    # Tier 1: records that explicitly apply to this consumer — a tombstone
    # (key-wide invalidation, applies to every consumer) or a rebind whose
    # replacement targets current_pr_number exactly. Latest created_at wins;
    # numeric suffix is only a same-timestamp tiebreak.
    applicable: list[tuple[datetime, str, Path, ModelReceiptSupersession]] = []
    for suffix, path, record, _err in loaded:
        if record is None:
            continue
        if record.tombstone:
            applicable.append((record.created_at, suffix, path, record))
            continue
        if (
            record.replacement is not None
            and record.replacement.pr_number == current_pr_number
        ):
            applicable.append((record.created_at, suffix, path, record))

    if applicable:
        applicable.sort(
            key=lambda item: (item[0], int(item[1]) if item[1].isdigit() else -1)
        )
        _, _, winner_path, winner_record = applicable[-1]
        return _resolution_from_record(winner_record, winner_path)

    # No record targets this consumer specifically — behave exactly as a
    # caller with no PR context would (legacy / untargeted chain).
    return _legacy_winner()


__all__ = ["SupersessionResolution", "resolve_supersession"]
