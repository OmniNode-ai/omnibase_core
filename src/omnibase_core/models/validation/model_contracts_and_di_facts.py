# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts the contracts-and-DI checker judges a pin against (OMN-21623).

A literal pin of a first-party package or reusable workflow is a finding only when
the pinned repository declares a dev-merge tag source and no advancer manifest
names the pin site. Both facts are read from the workspace by the validator, never
listed by hand: ``tag_source_repositories`` holds every repository whose clone
carries a file matching a row's ``tag_source_globs``, and ``advanced_sites`` holds
one ``<pinned repository>><consumer repository>:<repository-relative path>`` entry
per pin site an advancer manifest declares.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelContractsAndDiFacts"]


class ModelContractsAndDiFacts(BaseModel):
    """The scanned file's repository and the workspace pin facts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(
        description="Name of the repository the judged file belongs to."
    )
    tag_source_repositories: frozenset[str] = Field(
        default_factory=frozenset,
        description="Repositories that declare a dev-merge tag source.",
    )
    advanced_sites: frozenset[str] = Field(
        default_factory=frozenset,
        description=(
            "Pin sites an advancer manifest declares, each "
            "'<pinned repository>><consumer repository>:<path>'."
        ),
    )
