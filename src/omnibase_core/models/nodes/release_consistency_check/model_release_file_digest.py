# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One release file named with its sha256."""

from pydantic import BaseModel, ConfigDict


class ModelReleaseFileDigest(BaseModel):
    """A file name (no directory) and its lowercase hex sha256."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str
    sha256: str
