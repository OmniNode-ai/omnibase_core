#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-platform timeout exception."""

from __future__ import annotations

__all__ = ["TimeoutError"]


class TimeoutError(Exception):
    """Cross-platform timeout exception."""
