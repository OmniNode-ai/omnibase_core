# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_first_party_policy import (
    ModelFirstPartyPolicy,
)


class ModelThirdPartyRefParameters(ModelFirstPartyPolicy):
    github_org: str = Field(min_length=1)
    sha_pattern: str
    patterns: list[str]
