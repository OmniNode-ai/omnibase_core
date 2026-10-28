# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting type-check. Do not merge."""

def canary_typed() -> int:
    """Return a str where int is declared."""
    return "not an int"
