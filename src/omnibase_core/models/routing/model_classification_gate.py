# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Classification gate model for policy bundle tier constraints.

A classification gate maps a data classification level to the set of
resolution tiers where that data may be resolved, along with encryption
and redaction requirements.

.. versionadded:: 0.21.0
    Phase 4 of authenticated dependency resolution (OMN-2893).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_classification import EnumClassification
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier

__all__ = ["ModelClassificationGate"]


class ModelClassificationGate(BaseModel):
    """Constrains resolution tiers for a data classification level.

    Each gate defines which tiers are allowed for data at a given
    classification level, and whether encryption or redaction is
    required when resolving through those tiers.

    Attributes:
        classification: The data classification level this gate applies to.
        allowed_tiers: Resolution tiers permitted for this classification.
            An empty list means no tiers are allowed (effectively blocking
            resolution for this classification).
        require_encryption: Whether encryption is required for data at
            this classification level during resolution.
        require_redaction: Whether field-level redaction must be applied
            before resolution at the allowed tiers.
        redaction_policy: Name of the redaction policy to apply when
            ``require_redaction`` is True. None means no specific policy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    classification: EnumClassification = Field(
        description="Data classification level this gate applies to",
    )

    allowed_tiers: list[EnumResolutionTier] = Field(
        default_factory=list,
        description="Resolution tiers permitted for this classification",
    )

    require_encryption: bool = Field(
        default=False,
        description="Whether encryption is required for this classification",
    )

    require_redaction: bool = Field(
        default=False,
        description="Whether field-level redaction must be applied",
    )

    redaction_policy: str | None = Field(
        default=None,
        description="Name of the redaction policy to apply (e.g., 'pii_masked')",
    )
