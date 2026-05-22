# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context pack provenance enum for artifact origin classification."""

from __future__ import annotations

from enum import Enum


class EnumContextPackProvenance(str, Enum):
    """Origin classification for a context chunk artifact in a context pack.

    Distinct from EnumDataProvenance (dashboard display provenance).
    This enum classifies how context pack chunk content was produced.
    """

    GENERATED = "generated"
    CURATED = "curated"
    CACHED = "cached"
    OBSERVED = "observed"


__all__ = [
    "EnumContextPackProvenance",
]
