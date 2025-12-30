# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Profile Reference Model.

Reference to a default profile that a contract patch extends.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1125: Default Profile Factory for Contracts

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelProfileReference",
]


class ModelProfileReference(BaseModel):
    """Reference to a default profile that a contract patch extends.

    Profile references identify which base profile a contract patch should
    extend. The profile factory resolves these references to produce base
    contracts that patches are applied to.

    Attributes:
        profile: Profile identifier (e.g., "compute_pure", "orchestrator_safe").
        version: Profile version constraint (e.g., "1.0.0", "^1.0").

    Example:
        >>> ref = ModelProfileReference(
        ...     profile="compute_pure",
        ...     version="1.0.0",
        ... )
        >>> ref.profile
        'compute_pure'

    See Also:
        - ModelContractPatch: Uses this to specify which profile to extend
        - Default Profile Factory (OMN-1125): Resolves profile references
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    profile: str = Field(
        ...,
        min_length=1,
        description=(
            "Profile identifier (e.g., 'compute_pure', 'orchestrator_safe'). "
            "Must match a registered profile in the profile factory."
        ),
    )

    version: str = Field(
        ...,
        min_length=1,
        description=(
            "Profile version constraint (e.g., '1.0.0', '^1.0'). "
            "Uses semantic versioning format for version matching."
        ),
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelProfileReference(profile={self.profile!r}, version={self.version!r})"
        )
