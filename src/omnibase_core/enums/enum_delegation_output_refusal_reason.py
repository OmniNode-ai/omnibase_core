# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reasons a declared deliverable cannot be safely located."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationOutputRefusalReason(StrEnum):
    """Contract-defined reasons a response cannot become a customer deliverable."""

    AMBIGUOUS_UNMARKED_DELIVERABLE = "ambiguous_unmarked_deliverable"
    NO_SCHEMA_CONFORMING_JSON = "no_schema_conforming_json"


__all__ = ["EnumDelegationOutputRefusalReason"]
