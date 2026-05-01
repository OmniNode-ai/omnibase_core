# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File zone enum for tiered QA gate classification (OMN-10351)."""

from __future__ import annotations

from enum import StrEnum


class EnumFileZone(StrEnum):
    """Directory-role classification for per-zone QA gating.

    Distinct from EnumFileType (extension/format) — a .py file is PRODUCTION
    under src/ but TEST under tests/.
    """

    PRODUCTION = "production"
    TEST = "test"
    CONFIG = "config"
    GENERATED = "generated"
    DOCS = "docs"
    BUILD = "build"
