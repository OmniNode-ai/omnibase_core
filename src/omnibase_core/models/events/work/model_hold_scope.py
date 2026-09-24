# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a typed hold covers (OMN-16177, typed work ledger).

A scope is the union of its parts: the named PRs, the named repos (or every
repo), the named surfaces and the named lanes. The checker matches a question
against these fields only.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.events.work.model_pr_key import REPO_NAME_PATTERN, ModelPrKey

__all__ = ["ModelHoldScope"]

_NAME_MAX_LENGTH = 128


class ModelHoldScope(ModelEventPayloadBase):
    """The PRs, repos, surfaces and lanes a hold covers. Never empty. Hashable.

    Set-valued fields serialize as sorted lists, so the JSON form of one scope
    is byte-identical however its sets were built.
    """

    prs: frozenset[ModelPrKey] = Field(
        default_factory=frozenset, description="Pull requests covered."
    )
    repos: frozenset[Annotated[str, Field(pattern=REPO_NAME_PATTERN)]] = Field(
        default_factory=frozenset,
        description="Repositories covered, lower-cased. Empty when all_repos is set.",
    )
    all_repos: bool = Field(
        default=False,
        description="Covers every repository. Refused together with a non-empty repos.",
    )
    surfaces: frozenset[str] = Field(
        default_factory=frozenset,
        description="Proof surfaces covered, e.g. 'dogfood-105'. A lease names these.",
    )
    lanes: frozenset[str] = Field(
        default_factory=frozenset, description="Lanes covered."
    )

    @field_validator("repos", mode="before")
    @classmethod
    def _lower_repos(cls, raw: object) -> object:
        """Lower-case before the pattern check, as ``ModelPrKey.repo`` does."""
        if isinstance(raw, (set, frozenset, list, tuple)):
            return frozenset(
                repo.lower() if isinstance(repo, str) else repo for repo in raw
            )
        return raw

    @field_validator("surfaces", "lanes")
    @classmethod
    def _reject_blank_names(cls, raw: frozenset[str]) -> frozenset[str]:
        for name in raw:
            if not name.strip() or len(name) > _NAME_MAX_LENGTH:
                raise ValueError(
                    f"{name!r} must be non-blank and at most "
                    f"{_NAME_MAX_LENGTH} characters"
                )
        return raw

    @model_validator(mode="after")
    def _one_non_empty_spelling(self) -> ModelHoldScope:
        if not (
            self.prs or self.repos or self.all_repos or self.surfaces or self.lanes
        ):
            raise ValueError(
                "a hold scope must cover at least one PR, repo, surface or lane, "
                "or set all_repos"
            )
        if self.all_repos and self.repos:
            raise ValueError(
                "all_repos=True with a non-empty repos is two spellings of one "
                "scope; set one or the other"
            )
        return self

    @field_serializer("prs")
    def _serialize_prs_sorted(self, value: frozenset[ModelPrKey]) -> list[ModelPrKey]:
        return sorted(value, key=lambda key: (key.repo, key.number))

    @field_serializer("repos", "surfaces", "lanes")
    def _serialize_names_sorted(self, value: frozenset[str]) -> list[str]:
        return sorted(value)
