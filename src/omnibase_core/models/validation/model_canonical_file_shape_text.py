# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeText -- one tracked file's text, supplied as a fact (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCanonicalFileShapeText(BaseModel):
    """A repository-relative path with its decoded text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    text: str
