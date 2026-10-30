# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A parsed uv source and all its declared version constraints."""

from pydantic import BaseModel, ConfigDict


class ModelDevTagLineageCandidate(BaseModel):
    """A single in-scope source entry, independent of filesystem state."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    package: str
    url: str
    tag: str
    declared_specs: tuple[str, ...]
