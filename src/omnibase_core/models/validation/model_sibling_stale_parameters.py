# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)


class ModelSiblingStaleParameters(ModelSiblingParameters):
    tag_pattern: str
    max_trailing_merges: int = Field(gt=0, strict=True)
    max_trailing_hours: int = Field(gt=0, strict=True)
    timestamp_pattern: str
    timestamp_format: str
    url_template: str
    github_org: str
    git_binary: str
    timeout_seconds: int = Field(gt=0, strict=True)
    tag_arguments: list[str] = Field(min_length=1)
    tag_prefix: str
    peeled_suffix: str
