# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Selection supplied to the release-identity facts EFFECT node."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelReleaseIdentityGatherInput(BaseModel):
    """Repository and legacy CLI change selectors; no caller trust assertions."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str
    base: str | None = None
    explicit_paths: tuple[str, ...] = ()
    # OMN-23834: the version source the repository's gate demands; None keeps
    # the legacy static-version rule.
    required_version_source: Literal["static", "vcs"] | None = None
