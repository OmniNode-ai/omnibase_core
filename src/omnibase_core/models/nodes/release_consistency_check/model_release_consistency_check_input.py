# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Immutable facts consumed by the pure release-consistency validator."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.release_consistency_check.model_release_file_digest import (
    ModelReleaseFileDigest,
)


class ModelReleaseConsistencyCheckInput(BaseModel):
    """What one release built and what PyPI serves for its version.

    ``served_files`` is None when PyPI could not be read; an empty tuple is a
    read that listed no files. ``wheel_version_raw`` is None when no single built
    wheel, or no METADATA ``Version`` in it, could be read.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tag: str
    built_files: tuple[ModelReleaseFileDigest, ...] = ()
    # PEP 440 strings read verbatim from the wheel METADATA and the PyPI JSON
    # and compared as text, not SemVer (a dev build reads 1.2.3.dev4+gabc).
    wheel_version_raw: str | None = None
    served_version_raw: str | None = None
    served_files: tuple[ModelReleaseFileDigest, ...] | None = None
    runtime_errors: tuple[str, ...] = ()
