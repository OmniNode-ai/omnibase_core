# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Individual compliance check entry model.

.. versionadded:: OMN-7071
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelComplianceCheckEntry(BaseModel):
    """A single compliance check within a node's verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    detail: str | None = None
