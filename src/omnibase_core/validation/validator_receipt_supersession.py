# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Supersession-chain resolution for DoD receipts (OMN-13888, scope item 3).

A receipt key ``(<TICKET>, <EVIDENCE_ITEM>, <CHECK_TYPE>)`` maps to a base file::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.yaml

plus an append-only chain of net-new correction records::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.supersede.<NNNN>.yaml

The record with the highest zero-padded ``NNNN`` is authoritative. A tombstone
record (``tombstone: true``, no replacement) invalidates the key; a replacement
record re-binds the key to a new receipt embedded in the record. When no
supersession file exists, the key resolves to its base receipt file. No merged
file is ever edited — corrections are always net-new higher-numbered files.

This module keeps the path-local O(1) glob the receipt tree was built for; it
does not scan a global supersessions directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_receipt_supersession import (
    ModelReceiptSupersession,
)

_SUPERSEDE_NNNN_RE = re.compile(r"\.supersede\.(\d+)\.yaml$")


@dataclass(frozen=True)
class SupersessionResolution:
    """Outcome of resolving a receipt key's supersession chain.

    Exactly one of ``receipt``, ``tombstoned``, or ``error`` is meaningful:

    - ``receipt`` set → the key is re-bound to this replacement receipt.
    - ``tombstoned`` True → the key is deliberately invalidated (no active
      receipt); the caller must treat it as MISSING / non-satisfied.
    - ``error`` set → the latest supersession record is unreadable/invalid; the
      caller must fail closed.

    ``source_path`` names the record used, for operator-facing messages.
    """

    receipt: ModelDodReceipt | None
    tombstoned: bool
    error: str | None
    source_path: Path


def resolve_supersession(
    receipts_dir: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
) -> SupersessionResolution | None:
    """Resolve the active receipt for a key from its supersession chain.

    Returns ``None`` when no supersession file exists for the key — the caller
    then proceeds with the base receipt file exactly as before (backward
    compatible). Otherwise returns a :class:`SupersessionResolution` describing
    the re-bind, the tombstone, or a load error from the authoritative record.
    """
    key_dir = receipts_dir / ticket_id / evidence_item_id
    if not key_dir.is_dir():
        return None

    numbered: list[tuple[int, Path]] = []
    for candidate in key_dir.glob(f"{check_type}.supersede.*.yaml"):
        match = _SUPERSEDE_NNNN_RE.search(candidate.name)
        if match is not None:
            numbered.append((int(match.group(1)), candidate))
    if not numbered:
        return None

    numbered.sort(key=lambda item: item[0])
    _, latest_path = numbered[-1]

    try:
        with latest_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except (yaml.YAMLError, OSError) as exc:
        return SupersessionResolution(
            receipt=None,
            tombstoned=False,
            error=f"supersession record {latest_path} is unreadable: {exc}",
            source_path=latest_path,
        )

    try:
        record = ModelReceiptSupersession.model_validate(raw)
    except ValidationError as exc:
        return SupersessionResolution(
            receipt=None,
            tombstoned=False,
            error=f"supersession record {latest_path} is invalid: {exc}",
            source_path=latest_path,
        )

    if (record.ticket_id, record.evidence_item_id, record.check_type) != (
        ticket_id,
        evidence_item_id,
        check_type,
    ):
        return SupersessionResolution(
            receipt=None,
            tombstoned=False,
            error=(
                f"supersession record {latest_path} declares key "
                f"({record.ticket_id}, {record.evidence_item_id}, "
                f"{record.check_type}) but is filed under "
                f"({ticket_id}, {evidence_item_id}, {check_type})"
            ),
            source_path=latest_path,
        )

    if record.tombstone:
        return SupersessionResolution(
            receipt=None,
            tombstoned=True,
            error=None,
            source_path=latest_path,
        )

    return SupersessionResolution(
        receipt=record.replacement,
        tombstoned=False,
        error=None,
        source_path=latest_path,
    )


__all__ = ["SupersessionResolution", "resolve_supersession"]
