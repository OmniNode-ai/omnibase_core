# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Canonical model for specifying a regeneration target (artifact or directory).
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelRegenerationTarget(BaseModel):
    """
    Canonical model for specifying a regeneration target (artifact or directory).
    """

    model_config = ConfigDict(extra="forbid")

    path: Path
    type: str | None = None  # Optionally use an Enum for artifact type
