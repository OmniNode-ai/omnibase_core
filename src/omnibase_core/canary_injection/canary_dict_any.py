# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting dict-any. Do not merge."""

from typing import Any


def canary_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Echo."""
    return value
