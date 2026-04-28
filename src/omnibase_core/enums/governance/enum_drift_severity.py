# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drift severity classification for contract field-level changes."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDriftSeverity(StrEnum):
    """Severity of detected contract drift, ordered by impact.

    NONE         - hashes match; no changes detected.
    NON_BREAKING - changes to low-impact paths (description, metadata, docs).
    ADDITIVE     - new optional fields added; existing consumers unaffected.
    BREAKING     - fields removed, types changed, or algorithm/schema modified.
    """

    NONE = "NONE"
    NON_BREAKING = "NON_BREAKING"
    ADDITIVE = "ADDITIVE"
    BREAKING = "BREAKING"
