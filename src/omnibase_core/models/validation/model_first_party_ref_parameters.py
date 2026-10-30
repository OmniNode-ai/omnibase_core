# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_first_party_policy import (
    ModelFirstPartyPolicy,
)


class ModelFirstPartyRefParameters(ModelFirstPartyPolicy):
    github_org: str = Field(min_length=1)
    tag_pattern: str
    sha_pattern: str
    forbidden_refs: list[str]
    patterns: list[str]
    structured_globs: list[str]
