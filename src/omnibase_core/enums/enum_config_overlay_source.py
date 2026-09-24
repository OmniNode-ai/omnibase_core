# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Where a config overlay document was read from (OMN-19391).

A deployment reads exactly one source; the two are never layered (plan
``2026-09-23-remove-hardcoded-model-config`` section 3.1).
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumConfigOverlaySource(StrEnum):
    """The source an overlay document came from."""

    STORE = "store"
    """The config store, read through the container's bootstrap identity."""

    LOCAL_HOME = "local-home"
    """JSON files under the local install's config directory."""


__all__ = ["EnumConfigOverlaySource"]
