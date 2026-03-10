# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelMixinMappingCollection — collection of mixin-to-handler mappings.

Serialized as ``mixin_mappings.yaml`` for review and migration tracking.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_mixin_mapping import ModelMixinMapping

__all__ = ["ModelMixinMappingCollection"]


class ModelMixinMappingCollection(BaseModel):
    """Collection of mixin-to-handler mappings.

    Serialized as ``mixin_mappings.yaml`` for review and migration tracking.
    """

    mixins: list[ModelMixinMapping] = Field(
        default_factory=list,
        description="List of mixin-to-handler mappings",
    )
