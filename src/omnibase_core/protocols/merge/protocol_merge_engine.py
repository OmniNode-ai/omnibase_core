"""
ProtocolMergeEngine - Protocol for contract merge operations.

This protocol defines the interface for merging contract patches with base
profiles to produce expanded (complete) handler contracts. The merge process
follows deterministic rules for combining partial specifications.

Design:
    The merge engine implements the core principle:

        "User-authored files are patches, not full contracts."

    Patch files extend base profiles, and the engine resolves these
    references to produce complete contracts. The merge is:

        - Pure: No side effects, no global state access
        - Deterministic: Same inputs always produce same outputs
        - Non-mutating: Never modifies input patch or base profile
        - Conflict-aware: Detects and reports merge conflicts

    Merge semantics:
        - Scalars: Patch value overrides base value (if not None)
        - Dicts: Recursive merge (patch keys override/add to base)
        - Lists: Use explicit __add/__remove operations from patch

Usage:
    .. code-block:: python

        from omnibase_core.protocols.merge import ProtocolMergeEngine
        from omnibase_core.models.contracts import ModelContractPatch

        def expand_user_contract(
            engine: ProtocolMergeEngine,
            patch: ModelContractPatch,
        ) -> ModelHandlerContract:
            '''Expand a user-authored patch to a full contract.'''
            # First validate the patch
            conflicts = engine.detect_conflicts(patch)
            if conflicts:
                raise ValueError(f"Patch has {len(conflicts)} conflicts")

            # Perform the merge
            return engine.merge(patch)

Related:
    - OMN-1127: Typed Contract Merge Engine (this protocol)
    - OMN-1126: ModelContractPatch (User-authored patches)
    - OMN-1117: ModelHandlerContract (Expanded contract output)
    - ModelMergeConflict: Conflict detection results
    - ONEX Three-Layer Architecture documentation

.. versionadded:: 0.4.1
"""

from __future__ import annotations

__all__ = [
    "ProtocolMergeEngine",
]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_contract_patch import (
        ModelContractPatch,
    )
    from omnibase_core.models.contracts.model_handler_contract import (
        ModelHandlerContract,
    )
    from omnibase_core.models.merge.model_merge_conflict import ModelMergeConflict


@runtime_checkable
class ProtocolMergeEngine(Protocol):
    """
    Protocol interface for contract merge engines.

    Merge engines combine contract patches with base profiles to produce
    expanded (complete) contracts. The merge process follows deterministic
    rules to ensure reproducible results.

    Merge Strategy:
        1. Resolve profile reference from patch.extends
        2. Load base contract from profile factory
        3. Apply scalar overrides (patch value replaces base if not None)
        4. Recursively merge dict fields (descriptor, etc.)
        5. Apply list operations (__add/__remove for handlers, deps, etc.)
        6. Validate result against contract schema
        7. Return expanded contract or report conflicts

    Key Properties:
        - **Pure**: No side effects - merge depends only on inputs
        - **Deterministic**: Same patch always yields same contract
        - **Non-mutating**: Input patch and base profile are never modified
        - **Conflict-aware**: Detects type mismatches, schema violations, etc.

    Thread Safety:
        Implementations should be stateless and thread-safe. The merge
        process should not modify any shared state.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.merge import ProtocolMergeEngine
            from omnibase_core.models.contracts import (
                ModelContractPatch,
                ModelProfileReference,
                ModelDescriptorPatch,
            )

            class SimpleMergeEngine:
                '''Simple implementation of ProtocolMergeEngine.'''

                def __init__(self, profile_registry: ProfileRegistry):
                    self._registry = profile_registry

                def merge(self, patch: ModelContractPatch) -> ModelHandlerContract:
                    '''Merge patch with its base profile.'''
                    # Load base from profile
                    base = self._registry.get_base_contract(patch.extends)

                    # Apply overrides
                    merged = self._apply_overrides(base, patch)

                    # Apply list operations
                    merged = self._apply_list_ops(merged, patch)

                    return merged

                def detect_conflicts(
                    self, patch: ModelContractPatch
                ) -> list[ModelMergeConflict]:
                    '''Detect conflicts without merging.'''
                    conflicts = []
                    # ... validation logic
                    return conflicts

                def validate_patch(self, patch: ModelContractPatch) -> bool:
                    '''Check if patch can be merged cleanly.'''
                    return len(self.detect_conflicts(patch)) == 0

            # Verify protocol conformance
            engine: ProtocolMergeEngine = SimpleMergeEngine(registry)
            assert isinstance(engine, ProtocolMergeEngine)

    See Also:
        - :class:`~omnibase_core.models.contracts.model_contract_patch.ModelContractPatch`:
          User-authored contract patches
        - :class:`~omnibase_core.models.contracts.model_handler_contract.ModelHandlerContract`:
          Expanded contract output
        - :class:`~omnibase_core.models.merge.model_merge_conflict.ModelMergeConflict`:
          Conflict detection results

    .. versionadded:: 0.4.1
    """

    def merge(self, patch: ModelContractPatch) -> ModelHandlerContract:
        """
        Merge a contract patch with its base profile.

        The patch's ``extends`` field references the base profile. The engine
        resolves this reference, loads the base contract, and applies the
        patch overrides according to merge semantics.

        Merge Semantics:
            1. **Scalars**: Patch value overrides base value if patch value
               is not None. If patch value is None, base value is retained.
            2. **Dicts**: Recursive merge - patch keys override or add to
               base dict. Nested dicts are merged recursively.
            3. **Lists**: Uses explicit ``__add``/``__remove`` operations.
               Items in ``__add`` are appended, items in ``__remove`` are
               filtered out by name/identifier.

        Args:
            patch: Contract patch containing overrides and list operations.
                The patch must have a valid ``extends`` field referencing
                an existing profile.

        Returns:
            Expanded (complete) handler contract ready for registration.
            The returned contract includes:
            - All fields from base profile (not overridden)
            - Overridden fields from patch
            - Merged list fields (base + adds - removes)

        Raises:
            ModelOnexError: If profile cannot be resolved, merge fails due
                to conflicts, or the result fails schema validation.
                Error codes include:
                - PROFILE_NOT_FOUND: Referenced profile doesn't exist
                - MERGE_CONFLICT: Irreconcilable type/schema conflicts
                - VALIDATION_ERROR: Result fails contract validation

        Example:
            .. code-block:: python

                from omnibase_core.models.contracts import (
                    ModelContractPatch,
                    ModelProfileReference,
                    ModelDescriptorPatch,
                )

                # Create patch extending a profile
                patch = ModelContractPatch(
                    extends=ModelProfileReference(
                        profile="compute_pure",
                        version="1.0.0",
                    ),
                    name="my_compute_handler",
                    node_version=ModelSemVer(major=1, minor=0, patch=0),
                    descriptor=ModelDescriptorPatch(
                        timeout_ms=30000,
                        idempotent=True,
                    ),
                )

                # Merge to get expanded contract
                contract = engine.merge(patch)

                # Contract now has all base profile defaults plus overrides
                assert contract.name == "my_compute_handler"
                assert contract.descriptor.timeout_ms == 30000
        """
        ...

    def detect_conflicts(self, patch: ModelContractPatch) -> list[ModelMergeConflict]:
        """
        Detect potential conflicts without performing the merge.

        Useful for validation and dry-run scenarios. Identifies issues
        like type mismatches, schema violations, and list conflicts
        before attempting the actual merge.

        Conflict Types Detected:
            - **TYPE_MISMATCH**: Patch value type incompatible with base
            - **SCHEMA_VIOLATION**: Value violates contract schema
            - **LIST_CONFLICT**: Same item in both __add and __remove
            - **REQUIRED_MISSING**: Required field not provided
            - **CONSTRAINT_CONFLICT**: Conflicting constraints
            - **INCOMPATIBLE**: Fundamentally incompatible values

        Args:
            patch: Contract patch to validate against its base profile.

        Returns:
            List of detected conflicts. Empty list if no conflicts found.
            Each conflict includes:
            - Field path where conflict occurred
            - Base value and patch value
            - Conflict type classification
            - Human-readable message
            - Optional suggested resolution

        Note:
            This method does not raise exceptions for conflicts. It collects
            all conflicts and returns them for inspection. Use ``validate_patch``
            for a simple pass/fail check.

        Example:
            .. code-block:: python

                # Validate before merging
                conflicts = engine.detect_conflicts(patch)

                if conflicts:
                    for conflict in conflicts:
                        print(f"Conflict at {conflict.field}: {conflict.message}")
                        if conflict.suggested_resolution:
                            print(f"  Suggestion: {conflict.suggested_resolution}")
                else:
                    # Safe to merge
                    contract = engine.merge(patch)
        """
        ...

    def validate_patch(self, patch: ModelContractPatch) -> bool:
        """
        Validate that a patch can be merged without conflicts.

        Convenience method that returns True if ``detect_conflicts()``
        returns an empty list. Use this for simple pass/fail validation
        without needing to inspect individual conflicts.

        Args:
            patch: Contract patch to validate.

        Returns:
            True if patch is valid for merging (no conflicts detected),
            False if any conflicts would prevent clean merge.

        Example:
            .. code-block:: python

                # Simple validation
                if engine.validate_patch(patch):
                    contract = engine.merge(patch)
                else:
                    # Get details about what's wrong
                    conflicts = engine.detect_conflicts(patch)
                    handle_conflicts(conflicts)

        Note:
            This method is equivalent to::

                def validate_patch(self, patch):
                    return len(self.detect_conflicts(patch)) == 0

            Implementations may optimize this if conflict detection is
            expensive, stopping at the first conflict found.
        """
        ...
