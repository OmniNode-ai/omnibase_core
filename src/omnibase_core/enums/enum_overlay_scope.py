# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overlay scope enumeration for contract resolution.

Defines the hierarchy of overlay scopes used by the contract.resolve
compute node. Overlays are applied from broadest to narrowest scope,
with later scopes taking precedence over earlier ones.

.. versionadded:: OMN-2754
"""

from enum import Enum

__all__ = ["EnumOverlayScope"]


class EnumOverlayScope(str, Enum):
    """Scope levels for overlay application in contract resolution.

    Overlays are applied in order from broadest (base) to narrowest (session),
    with each level overriding values from the preceding level.

    Attributes:
        BASE: The root contract profile — the starting point before any overlay.
        ORG: Organization-wide policy overlay.
        PROJECT: Project-specific overlay; narrows org defaults.
        ENV: Environment overlay (e.g., staging vs. production).
        USER: Per-user override; narrows env settings.
        SESSION: Transient session-level overlay; highest precedence.

    Example:
        >>> scope = EnumOverlayScope.PROJECT
        >>> scope.value
        'project'
    """

    BASE = "base"
    ORG = "org"
    PROJECT = "project"
    ENV = "env"
    USER = "user"
    SESSION = "session"
