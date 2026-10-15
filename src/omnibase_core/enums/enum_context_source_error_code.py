# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed error codes for context-source requests and responses (OMN-18531 / TC.1)."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumContextSourceErrorCode(StrEnum):
    """Why a context-source exchange failed validation on either side.

    The two-sided check follows the archived search client's request and
    response validation: a request that fails validation and a response that
    fails validation each yield a typed error, never an empty result.
    """

    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"


__all__ = [
    "EnumContextSourceErrorCode",
]
