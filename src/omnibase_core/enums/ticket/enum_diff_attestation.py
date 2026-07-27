# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumDiffAttestation — diff-falsifiable claims a receipt may assert (OMN-13927).

A receipt's free-text ``actual_output`` can *claim* things about its own PR diff
("net-new-only", "no existing receipts modified"). The per-receipt honesty gate
(:mod:`omnibase_core.validation.validator_receipt_honesty`) has zero diff context
and structurally cannot catch a receipt that lies about its own diff — the class
that produced the OMN-13917 incident (OCC #3551 attested net-new-only while its
diff modified a merged contract + 4 merged receipts).

This enum is the closed v1 vocabulary of claims that are mechanically falsifiable
against ``git diff --name-status <base>...<head>``. General free-text claim
extraction is explicitly descoped (unbounded NLP, false-positive prone); only the
three members below plus two high-precision legacy regexes are honored by
:func:`omnibase_core.validation.validator_receipt_diff_consistency.check_diff_consistency`.
"""

from __future__ import annotations

from enum import StrEnum


class EnumDiffAttestation(StrEnum):
    """A diff-falsifiable attestation a receipt may declare.

    Each member has an exact predicate over the PR's ``--name-status`` diff; a
    contradicted attestation is a hard FAIL (blocks merge). See
    :func:`omnibase_core.validation.validator_receipt_diff_consistency.check_diff_consistency`.

    Members
    -------
    NET_NEW_ONLY
        Every diff entry under ``drift/dod_receipts/**`` and ``contracts/**``
        has status ``A`` (add). Any ``M``/``D``/``R``/``C`` under those prefixes
        contradicts the claim. This is the append-only claim at the diff level —
        it composes with ``validator_occ_append_only`` (per-entry hashing makes
        "appending never touches merged files" the normal case).
    RECEIPTS_UNMODIFIED
        No ``M``/``D``/``R``/``C`` entries under ``drift/dod_receipts/**``.
        Adding new receipt files is allowed; touching a merged one is not.
    CONTRACT_UNMODIFIED
        ``contracts/<ticket_id>.yaml`` is absent from the diff, or present with
        status ``A``. Any ``M``/``D``/``R``/``C`` of the ticket's own contract
        contradicts the claim.
    """

    NET_NEW_ONLY = "NET_NEW_ONLY"
    RECEIPTS_UNMODIFIED = "RECEIPTS_UNMODIFIED"
    CONTRACT_UNMODIFIED = "CONTRACT_UNMODIFIED"


__all__ = ["EnumDiffAttestation"]
