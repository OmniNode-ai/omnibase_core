# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Kind of a client binding row (OMN-18531; relocated from omnimarket by OMN-21093)."""

from enum import StrEnum


class EnumBindingKind(StrEnum):
    """REPLACING rows render into the mod module; ADDITIVE rows into user-settings command hooks."""

    REPLACING = "replacing"
    ADDITIVE = "additive"
