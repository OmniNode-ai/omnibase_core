# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""BAD: This file imports from fake_core.internal which is forbidden."""

from __future__ import annotations

from fake_core.internal._helper import internal_helper  # VIOLATION


def do_bad_thing() -> str:
    """Uses internal helper - this should fail validation."""
    return internal_helper()
