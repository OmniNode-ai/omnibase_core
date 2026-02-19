# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Privacy level enum for LLM model selection.

Provides strongly-typed privacy levels for model selection and routing
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPrivacyLevel(StrValueHelper, str, Enum):
    """Privacy levels for LLM model selection."""

    LOCAL_ONLY = "local_only"
    EXTERNAL_OK = "external_ok"
    ANY = "any"


__all__ = ["EnumPrivacyLevel"]
