# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direction a projection orders its rows by for a UI data binding (OMN-13130)."""

from enum import StrEnum

__all__ = ["EnumBindingOrderDirection"]


class EnumBindingOrderDirection(StrEnum):
    """Direction the upstream projection orders its rows by."""

    ASCENDING = "ascending"
    DESCENDING = "descending"
