# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting print-statements. Do not merge."""

def canary_print() -> None:
    """Print to stdout."""
    print("canary")
