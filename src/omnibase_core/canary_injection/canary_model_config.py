# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting hardcoded-model-config. Do not merge."""

CANARY_MODEL = "gpt-4o"


def canary_model() -> str:
    """Return a hard-coded model id."""
    return CANARY_MODEL
