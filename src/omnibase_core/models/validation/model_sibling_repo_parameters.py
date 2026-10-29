# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)


class ModelSiblingRepoParameters(ModelSiblingParameters):
    github_org: str
    url_template: str
