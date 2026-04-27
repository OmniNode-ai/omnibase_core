# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-probe verification status enum (OMN-9789)."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumReprobeStatus"]


class EnumReprobeStatus(StrEnum):
    """Outcome values for re-probe verification."""

    PASS = "PASS"
    FAIL = "FAIL"
