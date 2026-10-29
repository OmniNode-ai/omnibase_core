# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The kind of a shipped file the check reads."""

from __future__ import annotations

from enum import StrEnum


class EnumBindingSourceKind(StrEnum):
    """A contract, a handler module or a model module."""

    CONTRACT = "contract"
    HANDLER = "handler"
    MODEL = "model"
