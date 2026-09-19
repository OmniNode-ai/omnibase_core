# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared customer-facing shape for a delegation deliverable."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationOutputShape(StrEnum):
    """Supported contract-governed deliverable shapes."""

    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


__all__ = ["EnumDelegationOutputShape"]
