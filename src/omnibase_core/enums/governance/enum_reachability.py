# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reachability classification for static governance findings."""

from enum import StrEnum


class EnumReachability(StrEnum):
    """Whether a static finding is on executable production authority."""

    LIVE = "live"
    DEAD = "dead"
    TEST_HARNESS = "test_harness"


__all__ = ["EnumReachability"]
