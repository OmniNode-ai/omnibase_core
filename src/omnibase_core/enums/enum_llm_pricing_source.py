# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Provenance of an ``llm.pricing`` entry (OMN-19391).

Measured cost and a vendor's list price are different claims; every price
names which one it is (plan doctrine gate "measured vs estimated cost").
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumLlmPricingSource(StrEnum):
    """Where a per-token price came from."""

    MEASURED = "measured"
    """Computed from API-reported usage rows; the entry carries the evidence."""

    VENDOR_LIST = "vendor_list"
    """Copied from the vendor's published price list."""


__all__ = ["EnumLlmPricingSource"]
