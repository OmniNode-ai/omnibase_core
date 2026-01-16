"""
Contract Patch Model.

Partial contract overrides applied to default profiles.
Core principle: "User-authored files are patches, not full contracts."

Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1125: Default Profile Factory for Contracts

.. versionadded:: 0.4.0
"""

from typing import ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_utils import (
    detect_add_remove_conflicts,
    validate_onex_name_list,
    validate_string_list,
)

__all__ = [
    "ModelContractPatch",
]

# Module-level constants for list length limits.
# These are defined at module scope so they can be used in Field() declarations
# which evaluate at class definition time (before ClassVar is available).
_MAX_LIST_ITEMS: int = 100
_MAX_CAPABILITY_LIST_ITEMS: int = 50


class ModelContractPatch(BaseModel):
    """Partial contract that overrides a default profile.

    Contract patches represent user-authored partial specifications that
    extend a base contract produced by a profile factory. The core principle
    is: **"User-authored files are patches, not full contracts."**

    Architecture:
        Profile (Environment Policy)
            ↓ influences
        Behavior (Handler Configuration)
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

    List Field Normalization:
        Empty lists (``[]``) are automatically normalized to ``None`` for all
        ``__add`` and ``__remove`` list operation fields. This normalization
        is intentional for patch semantics:

        - **Rationale**: An empty list means "add/remove nothing" which is
          semantically equivalent to "no operation" and thus equivalent to
          omitting the field entirely (``None``).
        - **Consistency**: Normalizing ensures that ``has_list_operations()``
          and ``get_add_operations()`` behave consistently regardless of
          whether the user passed ``[]`` or omitted the field.

        Example equivalence::

            # These three forms are all equivalent after normalization:
            patch1 = ModelContractPatch(extends=ref, handlers__add=[])
            patch2 = ModelContractPatch(extends=ref, handlers__add=None)
            patch3 = ModelContractPatch(extends=ref)  # handlers__add omitted

            assert patch1.handlers__add is None
            assert patch2.handlers__add is None
            assert patch3.handlers__add is None

        This applies to all list operation fields: ``handlers__add``,
        ``handlers__remove``, ``dependencies__add``, ``dependencies__remove``,
        ``consumed_events__add``, ``consumed_events__remove``,
        ``capability_inputs__add``, ``capability_inputs__remove``,
        ``capability_outputs__add``, and ``capability_outputs__remove``.

    Attributes:
        extends: Reference to the profile this patch extends.
        name: Contract name (required for new contracts).
        node_version: Contract version (required for new contracts).
        description: Human-readable description.
        input_model: Override input model reference.
        output_model: Override output model reference.
        descriptor: Nested behavior overrides (via ModelDescriptorPatch).
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

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

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
    # Behavior Overrides (Three-Layer Architecture)
    # =========================================================================

    descriptor: ModelDescriptorPatch | None = Field(
        default=None,
        description="Nested behavior overrides for handler settings.",
    )

    # =========================================================================
    # List Operations - Handlers
    # =========================================================================

    # Maximum number of items in list operations to prevent excessive patches.
    # Uses module-level constant _MAX_LIST_ITEMS for single source of truth.
    MAX_LIST_ITEMS: ClassVar[int] = _MAX_LIST_ITEMS

    # Maximum number of items for capability list operations (more constrained).
    # Capabilities are typically fewer and more significant than handlers/events.
    # Uses module-level constant _MAX_CAPABILITY_LIST_ITEMS for single source of truth.
    MAX_CAPABILITY_LIST_ITEMS: ClassVar[int] = _MAX_CAPABILITY_LIST_ITEMS

    handlers__add: list[ModelHandlerSpec] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Handlers to add to the contract (max 100 items).",
    )

    handlers__remove: list[str] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Handler names to remove from the contract (max 100 items).",
    )

    # =========================================================================
    # List Operations - Dependencies
    # =========================================================================

    dependencies__add: list[ModelDependency] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Dependencies to add to the contract (max 100 items).",
    )

    dependencies__remove: list[str] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Dependency names to remove from the contract (max 100 items).",
    )

    # =========================================================================
    # List Operations - Events
    # =========================================================================

    consumed_events__add: list[str] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Event types to add to consumed events (max 100 items).",
    )

    consumed_events__remove: list[str] | None = Field(
        default=None,
        max_length=_MAX_LIST_ITEMS,
        description="Event types to remove from consumed events (max 100 items).",
    )

    # =========================================================================
    # List Operations - Capabilities
    # =========================================================================

    # Note: capability_inputs__add uses list[str] for now.
    # When ModelCapabilityDependency (OMN-1152) is merged, this can be updated
    # to use that model for richer capability requirements.
    capability_inputs__add: list[str] | None = Field(
        default=None,
        max_length=_MAX_CAPABILITY_LIST_ITEMS,
        description="Required capability names to add (max 50 items).",
    )

    capability_inputs__remove: list[str] | None = Field(
        default=None,
        max_length=_MAX_CAPABILITY_LIST_ITEMS,
        description="Required capability names to remove (max 50 items).",
    )

    capability_outputs__add: list[ModelCapabilityProvided] | None = Field(
        default=None,
        max_length=_MAX_CAPABILITY_LIST_ITEMS,
        description="Provided capabilities to add (max 50 items).",
    )

    capability_outputs__remove: list[str] | None = Field(
        default=None,
        max_length=_MAX_CAPABILITY_LIST_ITEMS,
        description="Provided capability names to remove (max 50 items).",
    )

    # =========================================================================
    # Field Validators
    # =========================================================================

    @field_validator(
        "handlers__add",
        "handlers__remove",
        "dependencies__add",
        "dependencies__remove",
        "consumed_events__add",
        "consumed_events__remove",
        "capability_inputs__add",
        "capability_inputs__remove",
        "capability_outputs__add",
        "capability_outputs__remove",
        mode="before",
    )
    @classmethod
    def normalize_empty_lists_to_none(
        cls, v: list[object] | None
    ) -> list[object] | None:
        """Convert empty lists to None for list operation fields.

        Empty lists in __add or __remove operations are semantically equivalent
        to "no operation" and should be normalized to None to prevent confusion
        and ensure consistent behavior during patch application.

        This normalization ensures the following three forms are equivalent::

            patch1 = ModelContractPatch(extends=ref, handlers__add=[])
            patch2 = ModelContractPatch(extends=ref, handlers__add=None)
            patch3 = ModelContractPatch(extends=ref)  # handlers__add omitted

            # All three result in:
            assert patch1.handlers__add is None
            assert patch2.handlers__add is None
            assert patch3.handlers__add is None

        This validation runs first (mode="before") so subsequent validators
        receive either None or a non-empty list, simplifying type narrowing
        in downstream code.

        Args:
            v: List value or None. Type is ``list[object]`` to handle all
                list types (ModelHandlerSpec, ModelDependency, str, etc.).

        Returns:
            None if the list is empty, otherwise the original list unchanged.

        Note:
            This validator only normalizes empty lists. Non-empty lists pass
            through unchanged and are validated by type-specific validators
            (e.g., validate_handlers_remove, validate_consumed_events).
        """
        if v is not None and len(v) == 0:
            return None
        return v

    @field_validator("handlers__remove", mode="before")
    @classmethod
    def validate_handlers_remove(cls, v: list[str] | None) -> list[str] | None:
        """Validate and normalize handler names in remove list.

        Handler names are stripped of whitespace and normalized to lowercase
        for consistent matching. Empty strings after stripping are rejected.

        Uses shared validation from validator_utils to reduce code duplication.

        Args:
            v: List of handler names to remove, or None.

        Returns:
            Validated and normalized handler names.

        Raises:
            ValueError: If any name is empty or contains invalid characters.
        """
        return validate_onex_name_list(v, "handlers__remove", normalize_lowercase=True)

    @field_validator("dependencies__remove", mode="before")
    @classmethod
    def validate_dependencies_remove(cls, v: list[str] | None) -> list[str] | None:
        """Validate dependency names in remove list.

        Dependency names are stripped of whitespace. Empty strings are rejected.
        Minimum length is 2 characters to ensure meaningful names.

        Uses shared validation from validator_utils to reduce code duplication.

        Args:
            v: List of dependency names to remove, or None.

        Returns:
            Validated dependency names.

        Raises:
            ValueError: If any name is empty or too short.
        """
        return validate_string_list(v, "dependencies__remove", min_length=2)

    @field_validator("consumed_events__add", "consumed_events__remove", mode="before")
    @classmethod
    def validate_consumed_events(cls, v: list[str] | None) -> list[str] | None:
        """Validate event type names in add/remove lists.

        Event type names are stripped of whitespace. Empty strings are rejected.
        Event types typically use dot-separated format (e.g., 'user.created').

        Uses shared validation from validator_utils to reduce code duplication.

        Args:
            v: List of event type names, or None.

        Returns:
            Validated event type names.

        Raises:
            ValueError: If any name is empty.
        """
        return validate_string_list(v, "consumed_events")

    @field_validator(
        "capability_inputs__add", "capability_inputs__remove", mode="before"
    )
    @classmethod
    def validate_capability_inputs(cls, v: list[str] | None) -> list[str] | None:
        """Validate and normalize capability input names.

        Capability names are stripped of whitespace and normalized to lowercase
        for consistent matching. Must contain only alphanumeric characters
        and underscores.

        Uses shared validation from validator_utils to reduce code duplication.

        Args:
            v: List of capability names, or None.

        Returns:
            Validated and normalized capability names.

        Raises:
            ValueError: If any name is empty or contains invalid characters.
        """
        return validate_onex_name_list(v, "capability_inputs", normalize_lowercase=True)

    @field_validator("capability_outputs__remove", mode="before")
    @classmethod
    def validate_capability_outputs_remove(
        cls, v: list[str] | None
    ) -> list[str] | None:
        """Validate and normalize capability output names in remove list.

        Capability names are stripped of whitespace and normalized to lowercase
        for consistent matching. Must contain only alphanumeric characters
        and underscores.

        Uses shared validation from validator_utils to reduce code duplication.

        Args:
            v: List of capability names to remove, or None.

        Returns:
            Validated and normalized capability names.

        Raises:
            ValueError: If any name is empty or contains invalid characters.
        """
        return validate_onex_name_list(
            v, "capability_outputs__remove", normalize_lowercase=True
        )

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _collect_conflicts(
        self,
        add_names: list[str] | None,
        remove_names: list[str] | None,
        field_name: str,
        all_conflicts: list[str],
    ) -> None:
        """Detect conflicts and append to results list if any found.

        Helper method to DRY up the repeated conflict detection pattern
        in validate_no_add_remove_conflicts. Detects if the same item
        appears in both add and remove lists.

        Type Narrowing:
            Both ``add_names`` and ``remove_names`` are typed as ``list[str] | None``
            because they may be None when the corresponding __add/__remove field
            is not set. The ``detect_add_remove_conflicts`` function handles None
            values gracefully, returning an empty list if either input is None.

        Args:
            add_names: List of names being added (already extracted from models).
                May be None if the __add field is not set.
            remove_names: List of names being removed.
                May be None if the __remove field is not set.
            field_name: Name of the field for error messages.
            all_conflicts: Mutable list to append conflict messages to.
                **This parameter is mutated in-place.** Conflict messages are
                appended directly to this list rather than returned.

        Returns:
            None. Results are accumulated via mutation of ``all_conflicts``.

        Note:
            **Mutation Pattern**: This method intentionally mutates ``all_conflicts``
            in-place rather than returning a new list. This design choice:

            1. **Reduces allocations**: Avoids creating intermediate lists when
               checking 5+ field pairs for conflicts in validate_no_add_remove_conflicts.
            2. **Simplifies aggregation**: The caller can check multiple field pairs
               in sequence, accumulating all conflicts into a single list.
            3. **Follows collector pattern**: Common in validation scenarios where
               multiple checks contribute to a unified error report.

            The tradeoff is reduced functional purity for improved performance
            and reduced boilerplate in the calling code.
        """
        conflicts = detect_add_remove_conflicts(add_names, remove_names, field_name)
        if conflicts:
            # Conflicts are already sorted by detect_add_remove_conflicts
            all_conflicts.append(f"{field_name}: {conflicts}")

    # =========================================================================
    # Model Validators
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

    @model_validator(mode="after")
    def validate_no_add_remove_conflicts(self) -> "ModelContractPatch":
        """Validate that no item appears in both add and remove lists.

        Detects conflicts where the same value is added and removed in a single
        patch, which would result in undefined or contradictory behavior.

        Checks the following list operation pairs:
            - handlers__add vs handlers__remove
            - dependencies__add vs dependencies__remove
            - consumed_events__add vs consumed_events__remove
            - capability_inputs__add vs capability_inputs__remove
            - capability_outputs__add vs capability_outputs__remove

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If any add/remove conflicts are detected.
        """
        all_conflicts: list[str] = []

        # Check handlers (extract names from ModelHandlerSpec)
        handler_add_names = (
            [h.name for h in self.handlers__add] if self.handlers__add else None
        )
        self._collect_conflicts(
            handler_add_names, self.handlers__remove, "handlers", all_conflicts
        )

        # Check dependencies (extract names from ModelDependency)
        dep_add_names = (
            [d.name for d in self.dependencies__add] if self.dependencies__add else None
        )
        self._collect_conflicts(
            dep_add_names, self.dependencies__remove, "dependencies", all_conflicts
        )

        # Check consumed_events (string lists, no extraction needed)
        self._collect_conflicts(
            self.consumed_events__add,
            self.consumed_events__remove,
            "consumed_events",
            all_conflicts,
        )

        # Check capability_inputs (string lists, no extraction needed)
        self._collect_conflicts(
            self.capability_inputs__add,
            self.capability_inputs__remove,
            "capability_inputs",
            all_conflicts,
        )

        # Check capability_outputs (extract names from ModelCapabilityProvided)
        cap_out_add_names = (
            [c.name for c in self.capability_outputs__add]
            if self.capability_outputs__add
            else None
        )
        self._collect_conflicts(
            cap_out_add_names,
            self.capability_outputs__remove,
            "capability_outputs",
            all_conflicts,
        )

        if all_conflicts:
            raise ValueError(
                "Conflicting add/remove operations detected. Cannot add and remove "
                f"the same item in a single patch: {'; '.join(all_conflicts)}"
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

        List operations use the __add and __remove suffix convention to
        declaratively specify items to add or remove from base contract lists.

        Returns:
            True if any __add or __remove field is set to a non-None value.
            Returns False if the patch only contains scalar overrides.

        Example:
            >>> patch = ModelContractPatch(
            ...     extends=ref,
            ...     handlers__add=[handler_spec]
            ... )
            >>> assert patch.has_list_operations()
        """
        list_fields = [
            self.handlers__add,
            self.handlers__remove,
            self.dependencies__add,
            self.dependencies__remove,
            self.consumed_events__add,
            self.consumed_events__remove,
            self.capability_inputs__add,
            self.capability_inputs__remove,
            self.capability_outputs__add,
            self.capability_outputs__remove,
        ]
        return any(f is not None for f in list_fields)

    def get_add_operations(self) -> dict[str, list[object]]:
        """Get all __add list operations as a dictionary.

        Collects all non-None __add fields into a dictionary keyed by
        the base field name (without the __add suffix).

        Returns:
            Dictionary mapping field names to their add lists. Only includes
            fields that have non-None values. Empty dict if no add operations.

        Example:
            >>> patch = ModelContractPatch(
            ...     extends=ref,
            ...     handlers__add=[handler1],
            ...     consumed_events__add=["event.created"]
            ... )
            >>> adds = patch.get_add_operations()
            >>> # adds == {"handlers": [handler1], "consumed_events": ["event.created"]}
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
        """Get all __remove list operations as a dictionary.

        Collects all non-None __remove fields into a dictionary keyed by
        the base field name (without the __remove suffix). Remove operations
        contain string identifiers (names) of items to remove.

        Returns:
            Dictionary mapping field names to their remove lists. Only includes
            fields that have non-None values. Empty dict if no remove operations.

        Example:
            >>> patch = ModelContractPatch(
            ...     extends=ref,
            ...     handlers__remove=["old_handler"],
            ...     dependencies__remove=["deprecated_dep"]
            ... )
            >>> removes = patch.get_remove_operations()
            >>> # removes == {"handlers": ["old_handler"], "dependencies": ["deprecated_dep"]}
        """
        result: dict[str, list[str]] = {}
        if self.handlers__remove:
            result["handlers"] = list(self.handlers__remove)
        if self.dependencies__remove:
            result["dependencies"] = list(self.dependencies__remove)
        if self.consumed_events__remove:
            result["consumed_events"] = list(self.consumed_events__remove)
        if self.capability_inputs__remove:
            result["capability_inputs"] = list(self.capability_inputs__remove)
        if self.capability_outputs__remove:
            result["capability_outputs"] = list(self.capability_outputs__remove)
        return result

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation indicating whether this is a new contract
            (with name) or an override patch (without identity fields).

        Example:
            >>> # New contract patch
            >>> str(new_patch)
            "ModelContractPatch(new='my_handler', extends='compute_pure')"

            >>> # Override patch
            >>> str(override_patch)
            "ModelContractPatch(override, extends='effect_http')"
        """
        if self.is_new_contract:
            return (
                f"ModelContractPatch(new={self.name!r}, "
                f"extends={self.extends.profile!r})"
            )
        return f"ModelContractPatch(override, extends={self.extends.profile!r})"
