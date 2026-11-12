# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Selection supplied to the release-consistency gather EFFECT node."""

from pydantic import BaseModel, ConfigDict


class ModelReleaseConsistencyGatherInput(BaseModel):
    """The release tag, the built dist directory and the saved PyPI JSON.

    ``pypi_json_path`` is None, or names a missing file, when PyPI could not
    be read; the facts then carry no served files and the report reads UNKNOWN.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tag: str
    dist_dir: str
    pypi_json_path: str | None = None
