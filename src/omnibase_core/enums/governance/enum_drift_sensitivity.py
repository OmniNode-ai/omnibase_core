# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drift sensitivity levels controlling which changes are surfaced."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDriftSensitivity(StrEnum):
    """Controls which change categories trigger a non-NONE drift severity.

    STRICT   - flag any structural change, including metadata/docs.
    STANDARD - flag breaking and additive changes only (default).
    LAX      - flag breaking changes only.
    """

    STRICT = "STRICT"
    STANDARD = "STANDARD"
    LAX = "LAX"
