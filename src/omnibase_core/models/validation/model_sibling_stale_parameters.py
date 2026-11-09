# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)


class ModelSiblingStaleParameters(ModelSiblingParameters):
    """Parameters of the ``stale_pin`` rule.

    The rule no longer judges a pin's age (OMN-23386, RULING 2026-11-09T21:54:25Z):
    a repository moves its pin on a sibling only when it needs something new from
    that sibling, so a pin that trails the newest dev tag by any number of merges or
    hours never fails a change. What remains is the tag inventory the rule reads and
    the check that a dev-merge tag a pin names exists in it; the rule id stays
    ``stale_pin`` so the baselines and callers that name it keep reading it.
    """

    tag_pattern: str
    url_template: str
    github_org: str
    git_binary: str
    timeout_seconds: int = Field(gt=0, strict=True)
    tag_arguments: list[str] = Field(min_length=1)
    tag_prefix: str
    peeled_suffix: str
