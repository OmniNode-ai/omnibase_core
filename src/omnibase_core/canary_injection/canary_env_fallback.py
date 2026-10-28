# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting env-fallbacks. Do not merge."""

import os


def canary_setting() -> str:
    """Read a setting with a silent default."""
    return os.environ.get("CANARY_SETTING", "fallback")
