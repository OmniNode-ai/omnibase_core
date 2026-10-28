# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting union-usage. Do not merge."""

from typing import Optional


def canary_optional(value: Optional[str]) -> Optional[str]:
    """Echo."""
    return value
