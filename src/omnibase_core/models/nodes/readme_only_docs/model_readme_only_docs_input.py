# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed repository request for the strict documentation EFFECT node."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelReadmeOnlyDocsInput(BaseModel):
    """Scan the entire Git index at root, including unchanged tracked files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    root: Path = Path()
