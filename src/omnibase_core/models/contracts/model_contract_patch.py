# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Patch Model.

Partial contract overrides applied to default profiles.
Core principle: "User authored files are patches, not full contracts."

Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1125: Default Profile Factory for Contracts

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "ModelContractPatch",
]


class ModelContractPatch(BaseModel):
    """Partial contract that overrides a default profile.

    Contract patches represent user-authored partial specifications that
    extend a base contract produced by a profile factory. The core principle
    is: **"User authored files are patches, not full contracts."**

    Architecture:
        Profile (Environment Policy)
            ↓ influences
        Descriptor (Handler Behavior)
            ↓ embedded in
        Contract (Authoring Surface) ← PATCHES TARGET THIS
            ↓ produced by
        Factory → Base Contract + Patch = Expanded Contract

    Patch Semantics:
        - Patches are partial and declarative
        - Unspecified fields retain base contract values
        - List operations use __add/__remove suffixes
        - Validation is structural, not resolutive

    New vs Override Contracts:
        - **New contracts**: Must specify name and node_version
        - **Override patches**: Cannot redefine identity fields

    Attributes:
        extends: Reference to the profile this patch extends.
        name: Contract name (required for new contracts).
        node_version: Contract version (required for new contracts).
        description: Human-readable description.
        input_model: Override input model reference.
        output_model: Override output model reference.
        descriptor: Nested descriptor overrides.
        handlers__add: Handlers to add to the contract.
        handlers__remove: Handler names to remove.
        dependencies__add: Dependencies to add.
        dependencies__remove: Dependency names to remove.
        consumed_events__add: Event types to add.
        consumed_events__remove: Event types to remove.
        capability_inputs__add: Required capabilities to add.
        capability_outputs__add: Provided capabilities to add.

    Example:
        >>> # Minimal patch extending a profile
        >>> patch = ModelContractPatch(
        ...     extends=ModelProfileReference(
        ...         profile="compute_pure",
        ...         version="1.0.0",
        ...     ),
        ... )

        >>> # New contract with identity
        >>> patch = ModelContractPatch(
        ...     extends=ModelProfileReference(
        ...         profile="effect_http",
        ...         version="1.0.0",
        ...     ),
        ...     name="my_http_handler",
        ...     node_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     description="Custom HTTP handler",
        ...     descriptor=ModelDescriptorPatch(
        ...         timeout_ms=30000,
        ...         idempotent=True,
        ...     ),
        ... )

    See Also:
        - ModelProfileReference: Profile to extend
        - ModelDescriptorPatch: Handler behavior overrides
        - ContractPatchValidator: Validates patches before merge
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    # =========================================================================
    # Profile Extension (Required)
    # =========================================================================

    extends: ModelProfileReference = Field(
        ...,
        description=(
            "Reference to the profile this patch extends. "
            "The profile factory resolves this to produce the base contract."
        ),
    )

    # =========================================================================
    # Identity Overrides (Required for new contracts)
    # =========================================================================

    name: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Contract name. Required for new contracts, forbidden for override patches."
        ),
    )

    node_version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Contract version. Required for new contracts, "
            "must use structured ModelSemVer format."
        ),
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the contract.",
    )

    # =========================================================================
    # Model Overrides
    # =========================================================================

    input_model: ModelReference | None = Field(
        default=None,
        description="Override the input model type reference.",
    )

    output_model: ModelReference | None = Field(
        default=None,
        description="Override the output model type reference.",
    )

    # =========================================================================
    # Descriptor Overrides (Three-Layer Architecture)
    # =========================================================================

    descriptor: ModelDescriptorPatch | None = Field(
        default=None,
        description="Nested descriptor overrides for handler behavior settings.",
    )

    # =========================================================================
    # List Operations - Handlers
    # =========================================================================

    handlers__add: list[ModelHandlerSpec] | None = Field(
        default=None,
        description="Handlers to add to the contract.",
    )

    handlers__remove: list[str] | None = Field(
        default=None,
        description="Handler names to remove from the contract.",
    )

    # =========================================================================
    # List Operations - Dependencies
    # =========================================================================

    dependencies__add: list[ModelDependency] | None = Field(
        default=None,
        description="Dependencies to add to the contract.",
    )

    dependencies__remove: list[str] | None = Field(
        default=None,
        description="Dependency names to remove from the contract.",
    )

    # =========================================================================
    # List Operations - Events
    # =========================================================================

    consumed_events__add: list[str] | None = Field(
        default=None,
        description="Event types to add to consumed events.",
    )

    consumed_events__remove: list[str] | None = Field(
        default=None,
        description="Event types to remove from consumed events.",
    )

    # =========================================================================
    # List Operations - Capabilities
    # =========================================================================

    # Note: capability_inputs__add uses list[str] for now.
    # When ModelCapabilityDependency (OMN-1152) is merged, this can be updated
    # to use that model for richer capability requirements.
    capability_inputs__add: list[str] | None = Field(
        default=None,
        description="Required capability names to add.",
    )

    capability_outputs__add: list[ModelCapabilityProvided] | None = Field(
        default=None,
        description="Provided capabilities to add.",
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_identity_consistency(self) -> "ModelContractPatch":
        """Validate identity field consistency.

        New contracts (those declaring a new identity) must specify both
        name and node_version. This prevents partial identity definitions.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If name is set without node_version or vice versa.
        """
        has_name = self.name is not None
        has_version = self.node_version is not None

        if has_name != has_version:
            if has_name:
                raise ValueError(
                    "Contract patch specifies 'name' but not 'node_version'. "
                    "New contracts must specify both name and node_version."
                )
            raise ValueError(
                "Contract patch specifies 'node_version' but not 'name'. "
                "New contracts must specify both name and node_version."
            )

        return self

    # =========================================================================
    # Helper Properties
    # =========================================================================

    @property
    def is_new_contract(self) -> bool:
        """Check if this patch defines a new contract identity.

        Returns:
            True if both name and node_version are specified.
        """
        return self.name is not None and self.node_version is not None

    @property
    def is_override_only(self) -> bool:
        """Check if this patch only overrides an existing contract.

        Returns:
            True if neither name nor node_version are specified.
        """
        return self.name is None and self.node_version is None

    def has_list_operations(self) -> bool:
        """Check if this patch contains any list operations.

        Returns:
            True if any __add or __remove field is set.
        """
        list_fields = [
            self.handlers__add,
            self.handlers__remove,
            self.dependencies__add,
            self.dependencies__remove,
            self.consumed_events__add,
            self.consumed_events__remove,
            self.capability_inputs__add,
            self.capability_outputs__add,
        ]
        return any(f is not None for f in list_fields)

    def get_add_operations(self) -> dict[str, list[object]]:
        """Get all __add list operations.

        Returns:
            Dictionary mapping field names to their add lists.
        """
        result: dict[str, list[object]] = {}
        if self.handlers__add:
            result["handlers"] = list(self.handlers__add)
        if self.dependencies__add:
            result["dependencies"] = list(self.dependencies__add)
        if self.consumed_events__add:
            result["consumed_events"] = list(self.consumed_events__add)
        if self.capability_inputs__add:
            result["capability_inputs"] = list(self.capability_inputs__add)
        if self.capability_outputs__add:
            result["capability_outputs"] = list(self.capability_outputs__add)
        return result

    def get_remove_operations(self) -> dict[str, list[str]]:
        """Get all __remove list operations.

        Returns:
            Dictionary mapping field names to their remove lists.
        """
        result: dict[str, list[str]] = {}
        if self.handlers__remove:
            result["handlers"] = list(self.handlers__remove)
        if self.dependencies__remove:
            result["dependencies"] = list(self.dependencies__remove)
        if self.consumed_events__remove:
            result["consumed_events"] = list(self.consumed_events__remove)
        return result

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        if self.is_new_contract:
            return (
                f"ModelContractPatch(new={self.name!r}, "
                f"extends={self.extends.profile!r})"
            )
        return f"ModelContractPatch(override, extends={self.extends.profile!r})"
