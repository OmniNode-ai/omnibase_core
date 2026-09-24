# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PR key: the only way a decision field names a pull request (OMN-16177).

``ModelPrRef`` is a citation: it carries the PR's observed ``state`` and, when
merged, its merge commit. A hold or a claim cannot use it as a key, because the
same PR would then compare unequal to itself once its state moved. This key is
``{repo, number}`` only, with the repo lower-cased on validation, so every
spelling of one PR is one key and hashes as one.
"""

from __future__ import annotations

from typing import Final

from pydantic import Field, field_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["REPO_NAME_PATTERN", "ModelPrKey"]

REPO_NAME_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9_.-]{0,99}$"
"""A repository name without the org, after lower-casing.

Shared with ``ModelHoldScope.repos`` so a PR key and a repo scope can never
disagree about how a repository is spelled.
"""


class ModelPrKey(ModelEventPayloadBase):
    """A pull request named by repository and number. Hashable."""

    repo: str = Field(
        ...,
        pattern=REPO_NAME_PATTERN,
        description=(
            "Repository name without the org, lower-cased on validation, "
            "e.g. 'omnibase_infra'."
        ),
    )
    number: int = Field(..., ge=1, description="Pull request number.")

    @field_validator("repo", mode="before")
    @classmethod
    def _lower_repo(cls, raw: object) -> object:
        """Lower-case before the pattern check, so every spelling is one key."""
        return raw.lower() if isinstance(raw, str) else raw
