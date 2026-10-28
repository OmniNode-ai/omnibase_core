# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting no-utcnow. Do not merge."""

import datetime


def canary_now() -> datetime.datetime:
    """Return naive UTC time."""
    return datetime.datetime.utcnow()
