# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)


class ModelSiblingStaleParameters(ModelSiblingParameters):
    """Parameters of the ``stale_pin`` rule.

    ``max_trailing_merges`` is a proxy for age, and it mis-scales with a
    sibling's landing rate: a repository merging twenty pull requests an hour
    passes fifty trailing merges in about two and a half hours, which is less
    time than its consumers' CI takes, so no pin bump of it can still be fresh
    when it lands. ``max_trailing_merges_by_repo`` lets such a sibling name its
    own bound and leaves the age bound to govern freshness.

    ``max_trailing_merges_by_repo`` takes ``<repo>=<limit>`` entries, the shape
    ``siblings`` already uses, because a rule's ``parameters`` are validated
    against a scalar-or-list union before this model is applied and a nested
    mapping is refused there. The repository name is spelled as the right-hand
    side of a ``siblings`` entry. A sibling named here uses its own limit; every
    other sibling keeps ``max_trailing_merges`` (OMN-22828).
    """

    tag_pattern: str
    max_trailing_merges: int = Field(gt=0, strict=True)
    max_trailing_merges_by_repo: list[str]
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
