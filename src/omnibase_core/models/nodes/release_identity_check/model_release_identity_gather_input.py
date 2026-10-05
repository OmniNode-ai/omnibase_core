# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Selection supplied to the release-identity facts EFFECT node."""

from pydantic import BaseModel, ConfigDict


class ModelReleaseIdentityGatherInput(BaseModel):
    """Repository and legacy CLI change selectors; no caller trust assertions."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str
    base: str | None = None
    explicit_paths: tuple[str, ...] = ()
