# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting raw-sqlite3. Do not merge."""

import sqlite3


def canary_connect() -> sqlite3.Connection:
    """Open a raw sqlite connection."""
    return sqlite3.connect(":memory:")
