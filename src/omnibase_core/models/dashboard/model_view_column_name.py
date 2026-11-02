# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Column / field identifier type for view field maps (OMN-21997)."""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

__all__ = ["VIEW_COLUMN_NAME_PATTERN", "ViewColumnName"]

#: A bare lowercase identifier. Operators, parentheses, dots, braces and spaces
#: cannot appear, so an expression cannot be spelled as a column name.
VIEW_COLUMN_NAME_PATTERN = r"^[a-z_][a-z0-9_]*$"

#: A column of an exposure, or a field of a row model.
ViewColumnName = Annotated[
    str, StringConstraints(pattern=VIEW_COLUMN_NAME_PATTERN, max_length=64)
]
