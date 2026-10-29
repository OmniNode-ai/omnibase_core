# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The request to bump one opted-in consumer's omnibase-core dev tag (OMN-21478)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDependencyPinBumpRequest"]


class ModelDependencyPinBumpRequest(BaseModel):
    """The manifest, the consumer, its checkout and the dev tag to pin."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest: Path
    repo: str
    repo_root: Path
    dependency_tag: str
