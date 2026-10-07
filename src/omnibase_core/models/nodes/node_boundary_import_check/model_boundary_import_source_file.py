# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inline source supplied at the EFFECT boundary."""

from pydantic import BaseModel, ConfigDict


class ModelBoundaryImportSourceFile(BaseModel):
    """Repository-relative POSIX path and Python source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    source: str
