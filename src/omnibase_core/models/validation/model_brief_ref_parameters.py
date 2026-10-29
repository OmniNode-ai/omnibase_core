# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


from omnibase_core.models.validation.model_first_party_policy import (
    ModelFirstPartyPolicy,
)


class ModelBriefRefParameters(ModelFirstPartyPolicy):
    release_pattern: str
    tag_pattern: str
    patterns: list[str]
