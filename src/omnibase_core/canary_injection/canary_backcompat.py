# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting backward-compat. Do not merge."""

def canary_new() -> int:
    """Return one."""
    return 1


# Deprecated alias kept for backwards compatibility with the old name.
canary_old = canary_new
