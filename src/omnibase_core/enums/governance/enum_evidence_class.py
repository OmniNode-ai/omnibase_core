# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumEvidenceClass — provenance class of a dod_evidence proof artifact.

The receipt-gate uses the evidence class to decide *what kind of proof* is
acceptable for a given dod_evidence check. UI / dashboard work cannot be
proven by a direct HTTP probe (curl / wget / httpx) against a backend port —
that proves the API responds, not that the dashboard renders the data through
its proxy origin. UI-class evidence must come from a Playwright run whose
captured network trace originates from the dashboard proxy origin, not a
direct backend port (OMN-13024, A-2).
"""

from __future__ import annotations

from enum import StrEnum


class EnumEvidenceClass(StrEnum):
    """Classification of a DoD receipt's proof surface.

    Members
    -------
    UI_DASHBOARD
        Evidence for UI / dashboard behavior. The receipt-gate requires this
        class to be proven by a Playwright run with a proxy-origin network
        trace; a direct ``curl``/``wget``/``httpx`` probe is rejected.
    BACKEND
        Evidence for backend / service behavior. A direct HTTP probe is an
        acceptable proof surface; the UI proxy-origin requirement does not
        apply. Set this explicitly to opt a legitimate HTTP-client receipt
        out of the UI-class gate.
    UNCLASSIFIED
        No UI/backend distinction asserted or inferred. Treated as not
        UI-class — the proxy-origin requirement does not apply.
    """

    UI_DASHBOARD = "ui_dashboard"
    BACKEND = "backend"
    UNCLASSIFIED = "unclassified"


__all__ = ["EnumEvidenceClass"]
