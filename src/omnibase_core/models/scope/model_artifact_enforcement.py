# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelArtifactEnforcement — per-artifact enforcement tier configuration.

Declares what outcome occurs when a scope predicate fires. Supports different
tiers for the default path vs. specific failure modes, allowing fine-grained
control without requiring separate hook variants.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_enforcement import EnumEnforcement


class ModelArtifactEnforcement(BaseModel):
    """
    Per-artifact enforcement tier configuration.

    Declares what outcome occurs when a scope predicate fires. Supports
    different tiers for the default path vs. specific failure modes, allowing
    fine-grained control without requiring separate hook variants.

    Overlay composition (OMN-9905):
        Overlays may downgrade enforcement (block -> warn, warn -> observe)
        to support tester or external-contributor profiles. Upgrades require
        explicit operator intent and are not auto-composed by the loader.
        See :meth:`~omnibase_core.enums.enum_enforcement.EnumEnforcement.can_downgrade_to`.

    Attributes:
        default:            Enforcement tier for the default (matching) path.
        non_matching_scope: Tier when the scope predicate does not match.
                            Defaults to 'observe' (skip silently).
        missing_dependency: Tier when a declared dependency is unavailable.
                            Defaults to 'observe' (skip silently).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    default: EnumEnforcement = Field(
        default=EnumEnforcement.BLOCK,
        description=(
            "Enforcement tier for the matching (default) path. "
            "'block' is the default for security-relevant hooks."
        ),
    )
    non_matching_scope: EnumEnforcement = Field(
        default=EnumEnforcement.OBSERVE,
        description=(
            "Enforcement tier when the scope predicate does not match. "
            "Defaults to 'observe' (log only; do not interrupt non-OmniNode sessions)."
        ),
    )
    missing_dependency: EnumEnforcement = Field(
        default=EnumEnforcement.OBSERVE,
        description=(
            "Enforcement tier when a declared dependency is unavailable. "
            "Defaults to 'observe' (skip silently if dep is missing)."
        ),
    )


__all__ = ["ModelArtifactEnforcement"]
