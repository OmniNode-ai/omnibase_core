# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_first_party_ref_parameters import (
    ModelFirstPartyRefParameters,
)


class ModelFirstPartyCrossParameters(ModelFirstPartyRefParameters):
    brief_globs: list[str]
    brief_patterns: list[str]
    literal_ref_keys: list[str] = Field(min_length=1)
    repository_keys: list[str] = Field(min_length=1)
    ref_keys: list[str] = Field(min_length=1)
