# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EnumRedactionPolicy: controls how tool-input content is captured in delegation envelopes."""

from __future__ import annotations

from enum import Enum


class EnumRedactionPolicy(str, Enum):
    """Controls how tool-input content is captured in the delegation envelope."""

    REDACT = "redact"
    HASH_ONLY = "hash_only"
    FULL_CAPTURE = "full_capture"


__all__ = ["EnumRedactionPolicy"]
