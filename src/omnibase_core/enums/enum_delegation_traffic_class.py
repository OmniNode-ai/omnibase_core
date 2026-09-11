# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Traffic classification for delegation request provenance."""

from __future__ import annotations

from enum import StrEnum


class EnumDelegationTrafficClass(StrEnum):
    """Declared origin class of a delegation request.

    ``UNCLASSIFIED`` is intentionally distinct from ``ORGANIC``. Older callers
    and callers without an authoritative classifier must not be relabelled as
    organic merely because they are not known to be synthetic.
    """

    UNCLASSIFIED = "unclassified"
    ORGANIC = "organic"
    SYNTHETIC = "synthetic"


__all__ = ["EnumDelegationTrafficClass"]
