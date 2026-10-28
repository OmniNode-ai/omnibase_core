# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting except-swallow. Do not merge."""

def canary_swallow() -> None:
    """Swallow every error."""
    try:
        int("x")
    except Exception:
        pass
