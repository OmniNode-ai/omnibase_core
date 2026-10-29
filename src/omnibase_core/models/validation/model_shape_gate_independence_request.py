# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The workflow files and directories the independence guard scans (OMN-20298)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelShapeGateIndependenceRequest"]


class ModelShapeGateIndependenceRequest(BaseModel):
    """The workflow files and directories the independence guard scans (OMN-20298)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[Path, ...] = ()
