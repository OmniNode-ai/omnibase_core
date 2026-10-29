# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-gate exemption vocabulary (OMN-21504 / T-Q1)."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumReceiptGateExemption(StrEnum):
    """An exemption that cannot admit a factory task-ticket citation."""

    DEPENDENCY_BOT = "dependency_bot"
    WRITER_APP_PIN_ONLY = "writer_app_pin_only"
    DOCS_ONLY_ZONE = "docs_only_zone"


__all__ = ["EnumReceiptGateExemption"]
