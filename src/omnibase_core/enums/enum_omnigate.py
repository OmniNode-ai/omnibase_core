# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate-specific enums."""

from __future__ import annotations

from enum import StrEnum


class EnumGateResponse(StrEnum):
    """Responses available when an OmniGate receipt is missing."""

    AUTO_CLOSE = "auto-close"
    LABEL = "label"
    COMMENT = "comment"


class EnumGateEnforcementAction(StrEnum):
    """Concrete action emitted by OmniGate verification."""

    PASS = "pass"
    FAIL = "fail"
    AUTO_CLOSE = "auto-close"
    LABEL = "label"
    COMMENT = "comment"


class EnumOmniGateCheckType(StrEnum):
    """OmniGate-specific check categories."""

    SHELL = "shell"
    VALIDATOR = "validator"


__all__ = [
    "EnumGateEnforcementAction",
    "EnumGateResponse",
    "EnumOmniGateCheckType",
]
