# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One banned transport import, rendered for output."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelTransportImportFinding(BaseModel):
    """A banned transport import with its source line and rendered message."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: str
    line: int
    module_name: str
    context: str
    message: str
