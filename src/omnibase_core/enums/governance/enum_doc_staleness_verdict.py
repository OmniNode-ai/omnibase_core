# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Document staleness verdict for doc freshness scanning."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDocStalenessVerdict(StrEnum):
    """Verdict for a document's freshness status.

    FRESH   - no broken references, doc updated after referenced code.
    STALE   - doc not updated in >30 days, referenced code changed recently.
    BROKEN  - has broken references (files/functions that do not exist).
    UNKNOWN - could not determine (e.g., no extractable references).
    """

    FRESH = "FRESH"
    STALE = "STALE"
    BROKEN = "BROKEN"
    UNKNOWN = "UNKNOWN"
