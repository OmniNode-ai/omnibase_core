# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
OnexIgnoreSection model.
"""

from pydantic import BaseModel, Field


class ModelOnexIgnoreSection(BaseModel):
    patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to ignore for this tool/type.",
    )
