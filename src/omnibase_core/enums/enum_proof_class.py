# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Proof-Class Enum (OMN-13977 doctrine, seam-completed by OMN-15911).

Defines the closed set of "which surface proves this claim" values named by the
root CLAUDE.md "Proof capacity" rule: every completion claim names its
proof_class, and "Done" is invalid without naming and reading the surface that
proves it.

- CODE_ONLY: a merged PR only; no runtime meaning was observed.
- RECEIPT_BOUND: an OCC receipt PASS on the correct (main) governance path,
  with no product PR (e.g. a pure read-only audit/investigation).
- DEPLOYED: an image was built and deployed to the target lane.
- LIVE_READBACK: behavior was observed on a live surface (gh/Linear/ssh/
  projection), independent of whether a PR exists.
- REPLAY_PROVEN: proven via deterministic replay / golden chain.
- PROD_PROVEN: proven on the prod lane specifically.

Disambiguation: ``omnimarket.enums.enum_proof_class.EnumProofClass`` is a
DIFFERENT, unrelated, narrower enum (``replay-proven`` /
``runtime-observed-only``) scoped to LLM evidence-bundle token-count
provenance for on-vs-off experiments (OMN-12794). It predates this doctrine
enum, shares one member name by coincidence, and must not be confused with or
imported in place of this one. This enum is the ticket/contract-level
proof-class field consumed by
``omnimarket.nodes.node_dod_verify.services.receipt_bound_evidence`` and
``durable_evidence_gate``.
"""

from __future__ import annotations

from enum import StrEnum


class EnumProofClass(StrEnum):
    """Which surface proves a ticket/contract completion claim.

    Intended for use as the ``proof_class`` field on ``ModelTicketContract``
    (OMN-15911). Values are lowercase-hyphenated strings to match the literal
    vocabulary already used across CLAUDE.md doctrine text, Linear ticket
    prose, and the ``omnimarket`` DurableEvidenceGate's receipt-bound
    discriminator (``RECEIPT_BOUND_PROOF_CLASS = "receipt-bound"`` in
    ``services/receipt_bound_evidence.py``, which reads this field verbatim
    off a raw yaml-loaded contract dict).
    """

    CODE_ONLY = "code-only"
    RECEIPT_BOUND = "receipt-bound"
    DEPLOYED = "deployed"
    LIVE_READBACK = "live-readback"
    REPLAY_PROVEN = "replay-proven"
    PROD_PROVEN = "prod-proven"


__all__ = [
    "EnumProofClass",
]
