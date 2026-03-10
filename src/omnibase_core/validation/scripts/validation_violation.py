#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidationViolation — represents a validation violation."""

from __future__ import annotations

from typing import NamedTuple

__all__ = ["ValidationViolation"]


class ValidationViolation(NamedTuple):
    """Represents a validation violation."""

    file_path: str
    line_number: int
    column: int
    field_name: str
    violation_type: str
    suggestion: str
