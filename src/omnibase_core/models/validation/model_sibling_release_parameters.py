# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)


class ModelSiblingReleaseParameters(ModelSiblingParameters):
    exact_pattern: str
