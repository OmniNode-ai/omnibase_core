"""
Contract merge engine implementation.

Merges contract patches with base profiles to produce expanded contracts.
This is the core component of the Typed Contract Merge Engine (OMN-1127).

The merge engine follows this process:
1. Load base contract from profile factory using patch.extends
2. Apply scalar overrides (name, version, description, etc.)
3. Apply nested behavior/descriptor merges
4. Apply list operations (dependencies, events, capabilities)
5. Validate and return the expanded contract

Architecture:
    Profile (Environment Policy)
        ↓ influences
    Behavior (Handler Configuration)
        ↓ embedded in
    Contract (Authoring Surface) ← PATCHES TARGET THIS
        ↓ produced by
    Factory → Base Contract + Patch = Expanded Contract (via MergeEngine)

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1125: Default Profile Factory for Contracts

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_merge_conflict_type import EnumMergeConflictType
from omnibase_core.enums.enum_node_archetype import EnumNodeArchetype
from omnibase_core.merge.merge_rules import (
    apply_list_operations,
    merge_scalar,
)
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.merge.model_merge_conflict import ModelMergeConflict
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_capability_provided import (
        ModelCapabilityProvided,
    )
    from omnibase_core.models.contracts.model_descriptor_patch import (
        ModelDescriptorPatch,
    )
    from omnibase_core.protocols.protocol_contract_profile_factory import (
        ProtocolContractProfileFactory,
    )
    from omnibase_core.protocols.protocol_contract_validation_event_emitter import (
        ProtocolContractValidationEventEmitter,
    )


__all__ = [
    "ContractMergeEngine",
]


# Profile prefix to EnumNodeType mapping
# Used to infer node type from profile names when not explicitly provided
_PROFILE_PREFIX_TO_NODE_TYPE: dict[str, EnumNodeType] = {
    "compute": EnumNodeType.COMPUTE_GENERIC,
    "effect": EnumNodeType.EFFECT_GENERIC,
    "reducer": EnumNodeType.REDUCER_GENERIC,
    "orchestrator": EnumNodeType.ORCHESTRATOR_GENERIC,
    "transformer": EnumNodeType.TRANSFORMER,
    "validator": EnumNodeType.VALIDATOR,
    "gateway": EnumNodeType.GATEWAY,
    "aggregator": EnumNodeType.AGGREGATOR,
}


class ContractMergeEngine:
    """
    Merge engine that combines contract patches with base profiles.

    The merge process:
    1. Load base contract from profile factory using patch.extends
    2. Apply scalar overrides (name, version, description, etc.)
    3. Apply nested behavior/descriptor merges
    4. Apply list operations (dependencies, events, capabilities)
    5. Validate and return the expanded contract

    The engine supports both new contracts (with name/version in patch) and
    override-only patches (extending existing contracts without new identity).

    Attributes:
        _profile_factory: Factory for resolving base contracts from profiles.

    Example:
        >>> factory = ContractProfileFactory()
        >>> engine = ContractMergeEngine(factory)
        >>> patch = ModelContractPatch(
        ...     extends=ModelProfileReference(
        ...         profile="compute_pure",
        ...         version="1.0.0",
        ...     ),
        ...     name="my_compute_handler",
        ...     node_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     description="Custom compute handler",
        ...     descriptor=ModelDescriptorPatch(timeout_ms=30000),
        ... )
        >>> contract = engine.merge(patch)
        >>> contract.name
        'my_compute_handler'

    Thread Safety:
        This class is stateless (aside from the injected factory) and
        thread-safe. Each call to merge() operates independently.

    See Also:
        - ModelContractPatch: Partial contract overrides
        - ModelHandlerContract: Full handler contract specification
        - ProtocolContractProfileFactory: Base contract resolution
    """

    def __init__(
        self,
        profile_factory: ProtocolContractProfileFactory,
        event_emitter: ProtocolContractValidationEventEmitter | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """
        Initialize with a profile factory for resolving base contracts.

        Args:
            profile_factory: Factory that provides base contracts for profiles.
                Must implement ProtocolContractProfileFactory protocol.
            event_emitter: Optional event emitter for merge lifecycle events.
                If provided, merge_started and merge_completed events will be
                emitted during merge operations.
            correlation_id: Optional correlation ID for event tracing across
                services. Passed through to all emitted events.

        Raises:
            ModelOnexError: If profile_factory is None.

        Example:
            >>> # Basic initialization (no events)
            >>> engine = ContractMergeEngine(profile_factory)
            >>>
            >>> # With event emission
            >>> engine = ContractMergeEngine(
            ...     profile_factory,
            ...     event_emitter=my_emitter,
            ...     correlation_id=uuid4(),
            ... )

        .. versionchanged:: 0.4.1
            Added event_emitter and correlation_id parameters for OMN-1151.
        """
        if profile_factory is None:
            raise ModelOnexError(
                message="profile_factory cannot be None",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        self._profile_factory = profile_factory
        self._event_emitter = event_emitter
        self._correlation_id = correlation_id

    def merge(
        self,
        patch: ModelContractPatch,
        node_type: EnumNodeType | None = None,
        run_id: UUID | None = None,
    ) -> ModelHandlerContract:
        """
        Merge patch with its base profile to produce expanded contract.

        Steps:
        1. Resolve base contract from patch.extends
        2. Apply scalar overrides (name, version, description, etc.)
        3. Apply descriptor merges (behavior configuration)
        4. Apply list operations for capabilities and dependencies
        5. Construct and validate final ModelHandlerContract

        If an event_emitter was provided during initialization, this method
        will emit merge_started and merge_completed events.

        Args:
            patch: Contract patch containing overrides to apply.
            node_type: Optional node type override. If not provided,
                will be inferred from the profile name or base contract.
            run_id: Optional run identifier for event correlation. If not
                provided, a new UUID will be generated.

        Returns:
            Expanded ModelHandlerContract with merged values.

        Raises:
            ModelOnexError: If profile cannot be resolved or merge fails.
            ValueError: If patch validation fails.

        Example:
            >>> contract = engine.merge(patch)
            >>> contract = engine.merge(patch, node_type=EnumNodeType.COMPUTE_GENERIC)
            >>> contract = engine.merge(patch, run_id=uuid4())

        .. versionchanged:: 0.4.1
            Added run_id parameter and event emission for OMN-1151.
        """
        # Import event models here to avoid circular imports at module level
        from omnibase_core.models.events.contract_validation import (
            ModelContractMergeCompletedEvent,
            ModelContractMergeStartedEvent,
        )

        # Generate run_id if not provided
        effective_run_id = run_id if run_id is not None else uuid4()

        # Start timing for duration tracking
        start_time_ns = time.perf_counter_ns()

        # Track changes for diff summary
        changes_applied: list[str] = []

        # Determine contract name for events (use patch name or default)
        event_contract_name = patch.name if patch.name else patch.extends.profile

        # Emit merge_started event if emitter is available
        if self._event_emitter is not None:
            started_event = ModelContractMergeStartedEvent.create(
                contract_name=event_contract_name,
                run_id=effective_run_id,
                merge_plan_name=None,
                profile_names=[patch.extends.profile],
                overlay_refs=[],
                resolver_config_hash=None,
                correlation_id=self._correlation_id,
            )
            self._event_emitter.emit_merge_started(started_event)

        # 1. Determine node type
        resolved_node_type = self._resolve_node_type(patch, node_type)

        # 2. Load base contract from factory
        base = self._profile_factory.get_profile(
            node_type=resolved_node_type,
            profile=patch.extends.profile,
            version=patch.extends.version,
        )

        # 3. Apply scalar overrides
        # For new contracts, patch provides name/version; for overrides, use base
        merged_name = merge_scalar(base.name, patch.name)
        if merged_name is None:
            raise ModelOnexError(
                message="Contract name cannot be None after merge",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="name",
                base_value=base.name,
                patch_value=patch.name,
            )

        # Track name override
        if patch.name is not None and patch.name != base.name:
            changes_applied.append(f"name: {base.name} -> {patch.name}")

        # Version handling: patch uses ModelSemVer, base uses ModelSemVer
        # Keep as ModelSemVer for ModelHandlerContract.contract_version field
        merged_contract_version: ModelSemVer = (
            patch.node_version if patch.node_version else base.contract_version
        )

        # Track version override
        if patch.node_version is not None:
            changes_applied.append(
                f"node_version: set to {patch.node_version} (base contract_version: {base.contract_version})"
            )

        merged_description = merge_scalar(base.description, patch.description)

        # Track description override
        if patch.description is not None and patch.description != base.description:
            changes_applied.append("description: updated")

        # Model references
        merged_input_model = merge_scalar(
            base.input_model,
            str(patch.input_model) if patch.input_model else None,
        )
        if merged_input_model is None:
            raise ModelOnexError(
                message="input_model cannot be None after merge",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="input_model",
            )

        # Track input_model override
        if patch.input_model is not None:
            changes_applied.append(
                f"input_model: {base.input_model} -> {patch.input_model}"
            )

        merged_output_model = merge_scalar(
            base.output_model,
            str(patch.output_model) if patch.output_model else None,
        )
        if merged_output_model is None:
            raise ModelOnexError(
                message="output_model cannot be None after merge",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="output_model",
            )

        # Track output_model override
        if patch.output_model is not None:
            changes_applied.append(
                f"output_model: {base.output_model} -> {patch.output_model}"
            )

        # 4. Apply descriptor/behavior merge
        merged_behavior = self._merge_behavior(base.behavior, patch.descriptor)

        # Track descriptor changes
        if patch.descriptor is not None:
            changes_applied.append("descriptor: updated")

        # 5. Apply list operations for capabilities
        merged_capability_inputs = self._merge_capability_inputs(
            base_inputs=merged_behavior.capability_inputs if merged_behavior else [],
            add_inputs=patch.capability_inputs__add,
            remove_inputs=patch.capability_inputs__remove,
        )

        # Track capability_inputs changes
        if patch.capability_inputs__add:
            changes_applied.append(
                f"capability_inputs: added {len(patch.capability_inputs__add)} items"
            )
        if patch.capability_inputs__remove:
            changes_applied.append(
                f"capability_inputs: removed {len(patch.capability_inputs__remove)} items"
            )

        merged_capability_outputs = self._merge_capability_outputs(
            base_outputs=merged_behavior.capability_outputs if merged_behavior else [],
            add_outputs=patch.capability_outputs__add,
            remove_outputs=patch.capability_outputs__remove,
        )

        # Track capability_outputs changes
        if patch.capability_outputs__add:
            changes_applied.append(
                f"capability_outputs: added {len(patch.capability_outputs__add)} items"
            )
        if patch.capability_outputs__remove:
            changes_applied.append(
                f"capability_outputs: removed {len(patch.capability_outputs__remove)} items"
            )

        # 6. Generate handler_id from name
        # Convention: node.<name> for handler identification
        handler_id = f"node.{merged_name.lower().replace(' ', '_')}"

        # 7. Construct final contract
        result = ModelHandlerContract(
            handler_id=handler_id,
            name=merged_name,
            contract_version=merged_contract_version,
            description=merged_description,
            descriptor=merged_behavior,
            capability_inputs=merged_capability_inputs,
            capability_outputs=merged_capability_outputs,
            input_model=merged_input_model,
            output_model=merged_output_model,
            tags=list(base.tags) if base.tags else [],
        )

        # 8. Emit merge_completed event if emitter is available
        if self._event_emitter is not None:
            # Detect conflicts only when needed for event emission
            conflicts = self.detect_conflicts(patch)
            conflicts_resolved_count = len(conflicts)

            # Calculate duration in milliseconds
            end_time_ns = time.perf_counter_ns()
            duration_ms = (end_time_ns - start_time_ns) // 1_000_000

            completed_event = ModelContractMergeCompletedEvent.create(
                contract_name=event_contract_name,
                run_id=effective_run_id,
                effective_contract_name=merged_name,
                duration_ms=duration_ms,
                effective_contract_hash=None,  # Could be computed if needed
                overlays_applied_count=0,  # No overlays in current implementation
                defaults_applied=True,  # Profile defaults are always applied
                warnings_count=conflicts_resolved_count,
                diff_ref="; ".join(changes_applied) if changes_applied else None,
                correlation_id=self._correlation_id,
            )
            self._event_emitter.emit_merge_completed(completed_event)

        return result

    def detect_conflicts(self, patch: ModelContractPatch) -> list[ModelMergeConflict]:
        """
        Detect potential merge conflicts without performing merge.

        Analyzes the patch for issues that would cause merge failures or
        produce inconsistent results. Does not resolve the base profile.

        Conflict Types Detected:
        - LIST_CONFLICT: Same item in both add and remove lists
        - TYPE_MISMATCH: Invalid field types in patch
        - REQUIRED_MISSING: Missing required fields for new contracts

        Args:
            patch: Contract patch to analyze.

        Returns:
            List of detected conflicts. Empty list if no conflicts.

        Example:
            >>> conflicts = engine.detect_conflicts(patch)
            >>> if conflicts:
            ...     for conflict in conflicts:
            ...         print(f"{conflict.field}: {conflict.message}")
        """
        conflicts: list[ModelMergeConflict] = []

        # Check for list add/remove conflicts
        self._detect_list_conflicts(patch, conflicts)

        # Check for new contract requirements
        if patch.is_new_contract:
            self._detect_new_contract_issues(patch, conflicts)

        # Check descriptor consistency
        if patch.descriptor:
            self._detect_descriptor_conflicts(patch, conflicts)

        return conflicts

    def validate_patch(self, patch: ModelContractPatch) -> bool:
        """
        Return True if patch can be merged without conflicts.

        Convenience method that checks if detect_conflicts returns empty list.

        Args:
            patch: Contract patch to validate.

        Returns:
            True if no conflicts detected, False otherwise.

        Example:
            >>> if engine.validate_patch(patch):
            ...     contract = engine.merge(patch)
        """
        return len(self.detect_conflicts(patch)) == 0

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _resolve_node_type(
        self,
        patch: ModelContractPatch,
        explicit_type: EnumNodeType | None,
    ) -> EnumNodeType:
        """
        Resolve node type from explicit value, profile name, or default.

        Resolution order:
        1. Explicit type parameter (if provided)
        2. Inferred from profile name prefix (e.g., "compute_pure" → COMPUTE_GENERIC)
        3. Default to COMPUTE_GENERIC

        Args:
            patch: Patch containing profile reference.
            explicit_type: Explicitly provided node type (takes precedence).

        Returns:
            Resolved EnumNodeType value.
        """
        if explicit_type is not None:
            return explicit_type

        # Try to infer from profile name prefix
        profile_name = patch.extends.profile.lower()
        for prefix, node_type in _PROFILE_PREFIX_TO_NODE_TYPE.items():
            if profile_name.startswith(prefix):
                return node_type

        # Default fallback
        return EnumNodeType.COMPUTE_GENERIC

    def _merge_behavior(
        self,
        base_behavior: ModelHandlerBehavior | None,
        patch_descriptor: ModelDescriptorPatch | None,
    ) -> ModelHandlerBehavior:
        """
        Merge base behavior with patch descriptor overrides.

        If base_behavior is None, creates a default behavior with patch overrides.
        If patch_descriptor is None, returns base behavior unchanged.

        Args:
            base_behavior: Base handler behavior from profile (may be None).
            patch_descriptor: Patch descriptor with overrides (may be None).

        Returns:
            Merged ModelHandlerBehavior with overrides applied.
        """
        # Import here to avoid circular import at module level

        # Default behavior if base is None
        if base_behavior is None:
            base_behavior = ModelHandlerBehavior(
                node_archetype=EnumNodeArchetype.COMPUTE,
                purity="side_effecting",
                idempotent=False,
            )

        # If no patch descriptor, return base unchanged
        if patch_descriptor is None:
            return base_behavior

        # Apply scalar overrides from patch to base
        # Handle idempotent explicitly since it's a required bool field
        merged_idempotent: bool = (
            patch_descriptor.idempotent
            if patch_descriptor.idempotent is not None
            else base_behavior.idempotent
        )

        return ModelHandlerBehavior(
            node_archetype=base_behavior.node_archetype,  # Archetype cannot be overridden
            purity=merge_scalar(base_behavior.purity, patch_descriptor.purity)
            or base_behavior.purity,
            idempotent=merged_idempotent,
            timeout_ms=merge_scalar(
                base_behavior.timeout_ms, patch_descriptor.timeout_ms
            ),
            retry_policy=merge_scalar(
                base_behavior.retry_policy, patch_descriptor.retry_policy
            ),
            circuit_breaker=merge_scalar(
                base_behavior.circuit_breaker, patch_descriptor.circuit_breaker
            ),
            concurrency_policy=merge_scalar(
                base_behavior.concurrency_policy, patch_descriptor.concurrency_policy
            )
            or base_behavior.concurrency_policy,
            isolation_policy=merge_scalar(
                base_behavior.isolation_policy, patch_descriptor.isolation_policy
            )
            or base_behavior.isolation_policy,
            observability_level=merge_scalar(
                base_behavior.observability_level, patch_descriptor.observability_level
            )
            or base_behavior.observability_level,
            capability_inputs=list(base_behavior.capability_inputs),
            capability_outputs=list(base_behavior.capability_outputs),
        )

    def _merge_capability_inputs(
        self,
        base_inputs: list[str],
        add_inputs: list[str] | None,
        remove_inputs: list[str] | None,
    ) -> list[ModelCapabilityDependency]:
        """
        Merge capability input lists using add/remove operations.

        Converts string capability names to ModelCapabilityDependency objects
        with default settings.

        Args:
            base_inputs: Base capability input names from behavior.
            add_inputs: Capability names to add (from patch).
            remove_inputs: Capability names to remove (from patch).

        Returns:
            List of ModelCapabilityDependency objects after merge.
        """
        # Apply list operations to string names
        merged_names: list[str] = apply_list_operations(
            base=list(base_inputs),
            add_items=add_inputs,
            remove_keys=remove_inputs,
            key_extractor=lambda x: x,
        )

        # Convert to ModelCapabilityDependency objects
        return [
            ModelCapabilityDependency(
                alias=name.replace(".", "_"),  # Use capability name as alias
                capability=name,
            )
            for name in merged_names
        ]

    def _merge_capability_outputs(
        self,
        base_outputs: list[str],
        add_outputs: list[ModelCapabilityProvided] | None,
        remove_outputs: list[str] | None,
    ) -> list[str]:
        """
        Merge capability output lists using add/remove operations.

        Args:
            base_outputs: Base capability output names.
            add_outputs: Capabilities to add (ModelCapabilityProvided objects).
            remove_outputs: Capability names to remove.

        Returns:
            List of capability output names after merge.
        """
        # Import here to avoid circular import

        # Extract names from add_outputs if provided
        add_names: list[str] | None = None
        if add_outputs:
            add_names = [cap.name for cap in add_outputs]

        # Apply list operations
        return apply_list_operations(
            base=list(base_outputs),
            add_items=add_names,
            remove_keys=remove_outputs,
            key_extractor=lambda x: x,
        )

    def _detect_list_conflicts(
        self,
        patch: ModelContractPatch,
        conflicts: list[ModelMergeConflict],
    ) -> None:
        """
        Detect add/remove conflicts in list operations.

        An item appearing in both add and remove lists is a conflict.
        This method checks all list operation pairs in the patch.

        Args:
            patch: Patch to analyze.
            conflicts: Mutable list to append detected conflicts to.
        """
        # Check capability_inputs
        if patch.capability_inputs__add and patch.capability_inputs__remove:
            add_set = set(patch.capability_inputs__add)
            remove_set = set(patch.capability_inputs__remove)
            overlap = add_set & remove_set
            if overlap:
                conflicts.append(
                    ModelMergeConflict(
                        field="capability_inputs",
                        base_value=list(remove_set),
                        patch_value={"add": list(add_set), "remove": list(remove_set)},
                        conflict_type=EnumMergeConflictType.LIST_CONFLICT,
                        message=f"Cannot add and remove same capability inputs: {sorted(overlap)}",
                        suggested_resolution="Remove conflicting items from either add or remove list",
                    )
                )

        # Check capability_outputs
        if patch.capability_outputs__add and patch.capability_outputs__remove:
            add_names = {cap.name for cap in patch.capability_outputs__add}
            remove_set = set(patch.capability_outputs__remove)
            overlap = add_names & remove_set
            if overlap:
                conflicts.append(
                    ModelMergeConflict(
                        field="capability_outputs",
                        base_value=list(remove_set),
                        patch_value={
                            "add": list(add_names),
                            "remove": list(remove_set),
                        },
                        conflict_type=EnumMergeConflictType.LIST_CONFLICT,
                        message=f"Cannot add and remove same capability outputs: {sorted(overlap)}",
                        suggested_resolution="Remove conflicting items from either add or remove list",
                    )
                )

        # Check handlers
        if patch.handlers__add and patch.handlers__remove:
            add_names = {h.name for h in patch.handlers__add}
            remove_set = set(patch.handlers__remove)
            overlap = add_names & remove_set
            if overlap:
                conflicts.append(
                    ModelMergeConflict(
                        field="handlers",
                        base_value=list(remove_set),
                        patch_value={
                            "add": list(add_names),
                            "remove": list(remove_set),
                        },
                        conflict_type=EnumMergeConflictType.LIST_CONFLICT,
                        message=f"Cannot add and remove same handlers: {sorted(overlap)}",
                        suggested_resolution="Remove conflicting handlers from either add or remove list",
                    )
                )

        # Check dependencies
        if patch.dependencies__add and patch.dependencies__remove:
            add_names = {d.name for d in patch.dependencies__add}
            remove_set = set(patch.dependencies__remove)
            overlap = add_names & remove_set
            if overlap:
                conflicts.append(
                    ModelMergeConflict(
                        field="dependencies",
                        base_value=list(remove_set),
                        patch_value={
                            "add": list(add_names),
                            "remove": list(remove_set),
                        },
                        conflict_type=EnumMergeConflictType.LIST_CONFLICT,
                        message=f"Cannot add and remove same dependencies: {sorted(overlap)}",
                        suggested_resolution="Remove conflicting dependencies from either add or remove list",
                    )
                )

        # Check consumed_events
        if patch.consumed_events__add and patch.consumed_events__remove:
            add_set = set(patch.consumed_events__add)
            remove_set = set(patch.consumed_events__remove)
            overlap = add_set & remove_set
            if overlap:
                conflicts.append(
                    ModelMergeConflict(
                        field="consumed_events",
                        base_value=list(remove_set),
                        patch_value={"add": list(add_set), "remove": list(remove_set)},
                        conflict_type=EnumMergeConflictType.LIST_CONFLICT,
                        message=f"Cannot add and remove same events: {sorted(overlap)}",
                        suggested_resolution="Remove conflicting events from either add or remove list",
                    )
                )

    def _detect_new_contract_issues(
        self,
        patch: ModelContractPatch,
        conflicts: list[ModelMergeConflict],
    ) -> None:
        """
        Detect issues specific to new contract definitions.

        New contracts must have consistent identity fields. The base
        implementation relies on ModelContractPatch's built-in validation
        and does not add additional checks.

        Note:
            This method serves as an extension point for subclasses to add
            custom validation for new contract definitions. Override this
            method to implement domain-specific validation rules.

        Example:
            >>> class CustomMergeEngine(ContractMergeEngine):
            ...     def _detect_new_contract_issues(
            ...         self,
            ...         patch: ModelContractPatch,
            ...         conflicts: list[ModelMergeConflict],
            ...     ) -> None:
            ...         # Add custom validation
            ...         if not patch.name.startswith("my_org_"):
            ...             conflicts.append(ModelMergeConflict(...))

        Args:
            patch: Patch to analyze.
            conflicts: Mutable list to append detected conflicts to.
        """
        # New contract validation is handled by ModelContractPatch itself
        # This method is a hook for additional validation if needed
        _ = patch  # stub-ok: extension point for subclass validation
        _ = conflicts  # stub-ok: extension point for subclass validation

    def _detect_descriptor_conflicts(
        self,
        patch: ModelContractPatch,
        conflicts: list[ModelMergeConflict],
    ) -> None:
        """
        Detect issues in descriptor/behavior patch.

        Checks for conflicting settings that would produce invalid behavior.
        The base implementation validates:

        - Retry policy consistency with idempotency (cannot retry non-idempotent)
        - Timeout consistency with retry (cannot retry with zero timeout)

        Note:
            This method serves as an extension point for subclasses to add
            custom descriptor validation. Override and call super() to extend
            the base validation rules with domain-specific checks.

        Example:
            >>> class CustomMergeEngine(ContractMergeEngine):
            ...     def _detect_descriptor_conflicts(
            ...         self,
            ...         patch: ModelContractPatch,
            ...         conflicts: list[ModelMergeConflict],
            ...     ) -> None:
            ...         # Call base implementation first
            ...         super()._detect_descriptor_conflicts(patch, conflicts)
            ...         # Add custom validation
            ...         if patch.descriptor and patch.descriptor.timeout_ms > 60000:
            ...             conflicts.append(ModelMergeConflict(...))

        Args:
            patch: Patch to analyze.
            conflicts: Mutable list to append detected conflicts to.
        """
        if not patch.descriptor:
            return

        descriptor = patch.descriptor

        # Check for retry without idempotency
        if descriptor.idempotent is False and descriptor.retry_policy is not None:
            if (
                descriptor.retry_policy.enabled
                and descriptor.retry_policy.max_retries > 0
            ):
                conflicts.append(
                    ModelMergeConflict(
                        field="descriptor.retry_policy",
                        base_value=None,
                        patch_value={
                            "idempotent": False,
                            "retry_enabled": True,
                        },
                        conflict_type=EnumMergeConflictType.CONSTRAINT_CONFLICT,
                        message="Cannot enable retry for non-idempotent handler",
                        suggested_resolution="Set idempotent=True or disable retry_policy",
                    )
                )

        # Check for zero timeout with retry
        if descriptor.timeout_ms == 0 and descriptor.retry_policy is not None:
            if (
                descriptor.retry_policy.enabled
                and descriptor.retry_policy.max_retries > 0
            ):
                conflicts.append(
                    ModelMergeConflict(
                        field="descriptor.timeout_ms",
                        base_value=None,
                        patch_value={
                            "timeout_ms": 0,
                            "retry_enabled": True,
                        },
                        conflict_type=EnumMergeConflictType.CONSTRAINT_CONFLICT,
                        message="Cannot enable retry with timeout_ms=0 (infinite wait)",
                        suggested_resolution="Set positive timeout_ms or disable retry_policy",
                    )
                )
