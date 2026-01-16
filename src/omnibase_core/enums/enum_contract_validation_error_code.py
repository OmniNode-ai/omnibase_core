"""Contract validation error codes for merge and expanded validation phases.

These error codes are used by the Contract Validation Pipeline to categorize
validation issues during Phase 2 (Merge Validation) and Phase 3 (Expanded
Contract Validation). They provide type-safe, machine-readable identification
of validation errors.

Error Code Categories:
    - Merge Validation (Phase 2): Issues during base+patch merging
    - Expanded Validation (Phase 3): Issues in fully-expanded contracts

Related:
    - OMN-1128: Contract Validation Pipeline
    - EnumPatchValidationErrorCode: Phase 1 patch-specific codes

.. versionadded:: 0.4.0
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContractValidationErrorCode(StrValueHelper, str, Enum):
    """Error codes for contract merge and expanded validation.

    These codes categorize the types of issues that can be detected
    during contract merge validation (Phase 2) and expanded contract
    validation (Phase 3). They are used in validation results to provide
    machine-readable issue identification.

    All error codes follow the CONTRACT_VALIDATION_* prefix convention for
    consistent categorization and type-safe identification.

    Phase 2 - Merge Validation:
        Validates the merge of base contract with patch overlays.

    Phase 3 - Expanded Contract Validation:
        Validates the fully-expanded contract for runtime correctness.

    Attributes:
        CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING: Required field not
            overridden in patch
        CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED: Placeholder value
            not replaced
        CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED: Dependency
            reference cannot be resolved
        CONTRACT_VALIDATION_MERGE_PROFILE_NOT_FOUND: Referenced profile does
            not exist
        CONTRACT_VALIDATION_MERGE_BASE_CONTRACT_INVALID: Base contract failed
            validation
        CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED: Merge conflict between
            base and patch
        CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE: Circular dependency
            in execution graph
        CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN: Handler with
            unresolved dependency
        CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID: Event routing
            configuration invalid
        CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING: No consumer for
            declared event
        CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH: Dependency type
            doesn't match expected
        CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED: Required capability
            cannot be satisfied
        CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED: Runtime
            invariant check failed
        CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID: Handler ID format
            invalid
        CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID: Input/output model
            reference invalid

    Example:
        >>> from omnibase_core.enums import EnumContractValidationErrorCode
        >>> code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        >>> result.add_error("Merge conflict in handlers", code=code.value)
    """

    # ==========================================================================
    # Phase 2: Merge Validation Errors
    # ==========================================================================

    CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING = (
        "CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING"
    )
    """Required field in base contract was not overridden by patch.

    Indicates that a field marked as required for override in the base
    contract was not provided in the patch. This typically applies to
    placeholder values that must be customized per deployment.
    """

    CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED = (
        "CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED"
    )
    """Placeholder value was not replaced during merge.

    Indicates that a placeholder value (e.g., '${PLACEHOLDER}' or
    'REQUIRED_OVERRIDE') still exists after merge. All placeholders
    must be resolved before the contract can be considered valid.
    """

    CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED = (
        "CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED"
    )
    """Dependency reference in merged contract cannot be resolved.

    Indicates that the merge result references a dependency (handler,
    model, or service) that cannot be found in the contract registry
    or dependency graph.
    """

    CONTRACT_VALIDATION_MERGE_PROFILE_NOT_FOUND = (
        "CONTRACT_VALIDATION_MERGE_PROFILE_NOT_FOUND"
    )
    """Referenced profile does not exist.

    Indicates that a profile referenced in the patch or base contract
    (via 'extends' or 'profile_ref') does not exist in the available
    profile registry.
    """

    CONTRACT_VALIDATION_MERGE_BASE_CONTRACT_INVALID = (
        "CONTRACT_VALIDATION_MERGE_BASE_CONTRACT_INVALID"
    )
    """Base contract failed validation before merge.

    Indicates that the base contract itself has validation errors that
    prevent merge from proceeding. The base contract must pass Phase 1
    validation before being used as a merge target.
    """

    CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED = (
        "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED"
    )
    """Merge conflict detected between base and patch.

    Indicates that the base contract and patch have conflicting values
    that cannot be automatically resolved. This may occur when both
    define incompatible settings for the same field without a clear
    override strategy.
    """

    # ==========================================================================
    # Phase 3: Expanded Contract Validation Errors
    # ==========================================================================

    CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE = (
        "CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE"
    )
    """Circular dependency detected in execution graph.

    Indicates that the handler dependency graph contains a cycle,
    making execution order undeterminable. All handler dependencies
    must form a directed acyclic graph (DAG).
    """

    CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN = (
        "CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN"
    )
    """Handler has unresolved dependency (orphan reference).

    Indicates that a handler declares a dependency on another handler
    that does not exist in the expanded contract. All handler
    dependencies must reference valid handler IDs.
    """

    CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID = (
        "CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID"
    )
    """Event routing configuration is invalid.

    Indicates that the event routing rules in the expanded contract
    are malformed or reference non-existent topics, handlers, or
    event types.
    """

    CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING = (
        "CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING"
    )
    """No consumer found for declared event.

    Indicates that an event type is declared as emitted but no handler
    is configured to consume it. This may indicate dead-letter events
    or missing handler configuration.
    """

    CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH = (
        "CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH"
    )
    """Dependency type does not match expected type.

    Indicates that a declared dependency has an incompatible type.
    For example, a handler expecting a COMPUTE node dependency
    receives an EFFECT node reference.
    """

    CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED = (
        "CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED"
    )
    """Required capability cannot be satisfied.

    Indicates that a handler or node requires a capability that
    cannot be provided by any registered service or runtime
    component.
    """

    CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED = (
        "CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED"
    )
    """Runtime invariant check failed.

    Indicates that the expanded contract violates a runtime invariant
    defined in the contract or system configuration. Invariants are
    conditions that must always hold for correct execution.
    """

    CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID = (
        "CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID"
    )
    """Handler ID format is invalid.

    Indicates that a handler ID does not conform to the expected
    format (e.g., must be lowercase_with_underscores, must not
    contain reserved characters).
    """

    CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID = (
        "CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID"
    )
    """Input or output model reference is invalid.

    Indicates that a handler's input_model or output_model reference
    cannot be resolved to a valid Pydantic model or schema definition.
    """


__all__ = ["EnumContractValidationErrorCode"]
