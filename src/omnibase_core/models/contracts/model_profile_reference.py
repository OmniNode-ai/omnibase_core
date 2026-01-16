"""
Profile Reference Model.

Reference to a default profile that a contract patch extends.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1125: Default Profile Factory for Contracts

.. versionadded:: 0.4.0
"""

from functools import cached_property

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_semver_constraint import ModelSemVerConstraint
from omnibase_core.models.primitives.model_semver import ModelSemVer

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

    @cached_property
    def _parsed_constraint(self) -> ModelSemVerConstraint:
        """Parse the version string into a constraint (cached).

        This property lazily parses the version constraint string into a
        ModelSemVerConstraint object. The result is cached for efficiency
        since ModelProfileReference is immutable (frozen=True).

        Returns:
            Parsed version constraint ready for matching.
        """
        return ModelSemVerConstraint.model_validate(self.version)

    def satisfies_version(self, version: ModelSemVer) -> bool:
        """Check if a version satisfies this profile's version constraint.

        Validates whether the given version falls within the bounds specified
        by the profile's version constraint. Supports various constraint formats:

        - Exact version: "1.0.0" (exact match)
        - Compatible version: "^1.0.0" (same major, >=1.0.0 <2.0.0)
        - Minimum version: "~1.0.0" or ">=1.0.0" (at least this version)
        - Range: ">=1.0.0,<2.0.0" (between versions)
        - Less than: "<2.0.0" (below this version)

        Args:
            version: The semantic version to validate against the constraint.

        Returns:
            True if the version satisfies the constraint, False otherwise.

        Example:
            >>> ref = ModelProfileReference(profile="compute_pure", version="^1.0.0")
            >>> ref.satisfies_version(ModelSemVer(major=1, minor=5, patch=0))
            True
            >>> ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0))
            False

        See Also:
            - ModelSemVerConstraint: The underlying constraint matching logic
        """
        return self._parsed_constraint.matches(version)
