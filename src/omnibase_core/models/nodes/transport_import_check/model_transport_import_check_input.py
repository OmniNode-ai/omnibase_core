# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Files and directories handed to the transport-import checker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelTransportImportCheckInput(BaseModel):
    """Paths (files or directories, scanned recursively) to check."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[str, ...] = ()
