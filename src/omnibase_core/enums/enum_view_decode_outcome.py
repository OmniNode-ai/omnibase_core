# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closed decode outcome vocabulary for view delivery receipts (OMN-21999).

A delivery receipt states whether the app decoded the received document and
whether a typed empty-state cause accompanies that outcome.
"""

from enum import StrEnum

__all__ = ["EnumViewDecodeOutcome"]


class EnumViewDecodeOutcome(StrEnum):
    """Outcome of decoding a view document received by the app."""

    DECODED = "decoded"
    """The document decoded without an empty-state cause."""

    DECODED_WITH_CAUSE = "decoded-with-cause"
    """The document decoded with a typed empty-state cause."""

    REFUSED = "refused"
    """The app refused the document with a typed cause."""
