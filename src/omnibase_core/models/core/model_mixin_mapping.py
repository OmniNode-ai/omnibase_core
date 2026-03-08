# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Mixin-to-handler mapping model for migration planning.

Provides a structured, serializable mapping from each mixin to its
handler conversion target, capability set, and nondeterminism classification.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.enums.enum_nondeterminism_class import EnumNondeterminismClass


class ModelMixinMapping(BaseModel):
    """Mapping from a mixin to its handler conversion target.

    Pure data artifact -- serializable, diffable, validator-friendly.
    No infra assumptions.

    Attributes:
        mixin_name: Class name of the mixin (e.g. ``MixinMetrics``).
        handler_contract_stub: Path to generated contract stub YAML.
        handler_type_category: Behavioral classification of the target handler.
        capability_set: List of capability identifiers this mixin provides.
        nondeterminism_classification: Source of nondeterminism in this mixin.
        legacy_shim_required: Whether a legacy compatibility shim is needed.
            Defaults to ``True`` until proven otherwise via conversion evidence.
        conversion_evidence: Evidence that legacy shim is not required.
            Required when ``legacy_shim_required`` is ``False``.
    """

    model_config = ConfigDict(extra="forbid")

    mixin_name: str = Field(description="Class name of the mixin")
    handler_contract_stub: str = Field(
        description="Path to generated handler contract stub"
    )
    handler_type_category: EnumHandlerTypeCategory = Field(
        description="Behavioral classification of the target handler"
    )
    capability_set: list[str] = Field(
        default_factory=list,
        description="Capability identifiers this mixin provides",
    )
    nondeterminism_classification: EnumNondeterminismClass = Field(
        description="Source of nondeterminism in this mixin"
    )
    legacy_shim_required: bool = Field(
        default=True,
        description="Whether a legacy compatibility shim is needed. "
        "Default True until proven otherwise.",
    )
    conversion_evidence: str | None = Field(
        default=None,
        description="Evidence that legacy shim is not required. "
        "Format: test:<name>, rule:<name>, or audit:YYYY-MM-DD",
    )

    @model_validator(mode="after")
    def _check_conversion_evidence(self) -> ModelMixinMapping:
        """Enforce conversion_evidence when legacy_shim_required is False."""
        if not self.legacy_shim_required and not self.conversion_evidence:
            raise ValueError(
                f"conversion_evidence is required when legacy_shim_required=False "
                f"for mixin '{self.mixin_name}'"
            )
        return self


class ModelMixinMappingCollection(BaseModel):
    """Collection of mixin-to-handler mappings.

    Serialized as ``mixin_mappings.yaml`` for review and migration tracking.
    """

    mixins: list[ModelMixinMapping] = Field(
        default_factory=list,
        description="List of mixin-to-handler mappings",
    )


__all__ = ["ModelMixinMapping", "ModelMixinMappingCollection"]
