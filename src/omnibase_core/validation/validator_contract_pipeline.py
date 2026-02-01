"""
Contract Validation Pipeline Orchestrator.

Coordinates multi-phase contract validation through three sequential phases:
    - Phase 1 (PATCH): Validates individual patches before merge
    - Phase 2 (MERGE): Validates merged contracts before expansion
    - Phase 3 (EXPANDED): Validates fully expanded contracts

Pipeline Flow:
    PATCH -> MERGE -> EXPANDED

The pipeline orchestrates all three validation phases and provides a unified
interface for validating contract patches through to fully expanded contracts.

Architecture:
    ContractValidationPipeline
        ├── ContractPatchValidator (Phase 1)
        ├── MergeValidator (Phase 2)
        │   └── constraint_validator (duck-typed seam for SPI)
        ├── ExpandedContractValidator (Phase 3)
        └── ContractMergeEngine (merge operation)

Duck-Typed Seam:
    The pipeline provides a duck-typed seam for future SPI constraint validator
    integration. Any object with a `validate(base, patch, merged)` method that
    returns a ModelValidationResult-compatible object can be injected.

    For type safety, implementations can follow ProtocolConstraintValidator,
    which documents the expected interface. However, duck typing is fully
    supported - implementations do not need to inherit from the protocol.

Logging Conventions:
    - DEBUG: Detailed trace information (phase transitions, validation steps)
    - INFO: High-level operation summaries (pipeline started/completed/failed)
    - WARNING: Recoverable issues that don't fail the pipeline
    - ERROR: Failures that halt pipeline execution

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractPatchValidator: Phase 1 validation
    - MergeValidator: Phase 2 validation
    - ExpandedContractValidator: Phase 3 validation
    - ContractMergeEngine: Merge operations
    - EnumValidationPhase: Pipeline phase enumeration
    - ProtocolConstraintValidator: Interface for custom constraint validators
    - ProtocolConstraintValidationResult: Result interface for constraint validators

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.events.contract_validation import (
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
    ModelContractValidationContext,
    ModelContractValidationEventBase,
    ModelContractValidationFailedEvent,
    ModelContractValidationPassedEvent,
    ModelContractValidationStartedEvent,
)
from omnibase_core.models.validation.model_expanded_contract_result import (
    ModelExpandedContractResult,
)
from omnibase_core.protocols.validation.protocol_contract_validation_event_emitter import (
    ProtocolContractValidationEventEmitter,
)
from omnibase_core.protocols.validation.protocol_contract_validation_pipeline import (
    ProtocolContractValidationPipeline,
)
from omnibase_core.validation.phases.validator_expanded_contract import (
    ExpandedContractValidator,
)
from omnibase_core.validation.phases.validator_merge import MergeValidator
from omnibase_core.validation.validator_contract_patch import ContractPatchValidator

if TYPE_CHECKING:
    from omnibase_core.protocols.protocol_contract_profile_factory import (
        ProtocolContractProfileFactory,
    )

__all__ = [
    "ContractValidationPipeline",
    "ModelExpandedContractResult",
    "ProtocolContractValidationPipeline",
]

# Configure logger for this module
logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Implementation
# =============================================================================


class ContractValidationPipeline:  # naming-ok: validator class, not protocol
    """Orchestrates multi-phase contract validation.

    The pipeline coordinates three validation phases:
        1. PATCH: Validates the patch structure and semantics
        2. MERGE: Validates the merge result for consistency
        3. EXPANDED: Validates the expanded contract for runtime correctness

    The pipeline stops on the first phase that produces critical errors,
    preserving results from previous phases.

    Duck-Typed Constraint Validator Seam:
        An optional constraint_validator can be injected for Phase 2 validation.
        Any object with a `validate(base, patch, merged)` method that returns
        a ModelValidationResult-compatible object will be called. This provides
        a seam for future SPI constraint validator integration.

        For type safety and documentation, implementations can follow the
        ProtocolConstraintValidator protocol, but this is optional. Duck typing
        is fully supported.

        The constraint validator is called during validate_merge() if provided.
        Its results are merged with the MergeValidator results.

    Thread Safety:
        This class is stateless (aside from injected validators) and thread-safe.
        Each call to validate_all() operates independently.

    Example:
        >>> # Basic usage with default validators
        >>> pipeline = ContractValidationPipeline()
        >>> result = pipeline.validate_all(patch, profile_factory)
        >>> if result.success:
        ...     print(f"Contract validated: {result.contract.name}")
        ... else:
        ...     # Handle validation failure
        ...     print(f"Validation failed at phase: {result.phase_failed}")
        ...     for error in result.errors:
        ...         print(f"  - {error}")
        ...
        >>> # With custom constraint validator
        >>> constraint_validator = MyConstraintValidator()
        >>> pipeline = ContractValidationPipeline(
        ...     constraint_validator=constraint_validator
        ... )
        >>> result = pipeline.validate_all(patch, profile_factory)

    Error Handling:
        When validation fails, the pipeline provides detailed error information.
        The ``phase_failed`` attribute indicates which phase first encountered
        critical errors, and ``validation_results`` contains detailed diagnostics
        for each executed phase.

        >>> from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
        >>> from omnibase_core.enums import EnumSeverity
        >>>
        >>> result = pipeline.validate_all(patch, profile_factory)
        >>> if not result.success:
        ...     # Determine which phase failed and provide appropriate guidance
        ...     if result.phase_failed == EnumValidationPhase.PATCH:
        ...         print("Patch structure is invalid - check patch definition")
        ...     elif result.phase_failed == EnumValidationPhase.MERGE:
        ...         print("Merge produced inconsistent result - check base/patch compatibility")
        ...     elif result.phase_failed == EnumValidationPhase.EXPANDED:
        ...         print("Expanded contract fails runtime validation - check handler references")
        ...
        ...     # Access phase-specific results for detailed diagnostics
        ...     for phase_name, phase_result in result.validation_results.items():
        ...         if not phase_result.is_valid:
        ...             print(f"\nPhase {phase_name}: {phase_result.error_level_count} errors, "
        ...                   f"{phase_result.warning_count} warnings")
        ...
        ...             # Iterate over all issues with full context
        ...             for issue in phase_result.issues:
        ...                 print(f"  [{issue.severity.value}] {issue.message}")
        ...                 if issue.code:
        ...                     print(f"    Code: {issue.code}")
        ...                 if issue.suggestion:
        ...                     print(f"    Suggestion: {issue.suggestion}")
        ...                 if issue.context:
        ...                     for key, value in issue.context.items():
        ...                         print(f"    {key}: {value}")
        ...
        ...     # Alternatively, filter issues by severity
        ...     for phase_name, phase_result in result.validation_results.items():
        ...         critical = phase_result.get_issues_by_severity(
        ...             EnumSeverity.CRITICAL
        ...         )
        ...         if critical:
        ...             print(f"CRITICAL issues in {phase_name}:")
        ...             for issue in critical:
        ...                 print(f"  - {issue.message}")

    Attributes:
        _constraint_validator: Optional duck-typed validator for Phase 2.
        _patch_validator: Phase 1 validator (ContractPatchValidator).
        _merge_validator: Phase 2 validator (MergeValidator).
        _expanded_validator: Phase 3 validator (ExpandedContractValidator).
        _event_emitter: Optional event emitter for lifecycle events. When
            provided, the pipeline emits events at each stage (started,
            merge_started, merge_completed, passed/failed).
        _correlation_id: Correlation ID for request tracing. All emitted
            events include this ID for cross-service tracing.

    See Also:
        - ContractPatchValidator: Phase 1 validation
        - MergeValidator: Phase 2 validation
        - ExpandedContractValidator: Phase 3 validation
        - ContractMergeEngine: Merge operations
        - ProtocolConstraintValidator: Interface for constraint validators
        - ProtocolConstraintValidationResult: Result interface
        - ProtocolContractValidationEventEmitter: Event emission interface

    Design Decisions:
        Sequential vs Lazy Validation: The current implementation validates
        all three phases sequentially (PATCH -> MERGE -> EXPANDED). While lazy
        validation (only validating phases that are needed) could improve
        performance for some use cases, the sequential approach was chosen for:

        1. Simplicity: Easier to reason about and debug
        2. Fail-fast: Catches errors early in the pipeline
        3. Consistency: All contracts go through the same validation path

        Lazy validation could be considered for future optimization if
        profiling shows significant performance impact from unused phases.
        Potential implementations could include:

        - Phase selection parameter in validate_all()
        - Separate methods for partial validation workflows
        - Caching of intermediate results for repeated validations
    """

    # Mapping from profile name prefixes to node types for base contract resolution
    _PREFIX_TO_NODE_TYPE_MAP: dict[str, EnumNodeType] = {
        "compute": EnumNodeType.COMPUTE_GENERIC,
        "effect": EnumNodeType.EFFECT_GENERIC,
        "reducer": EnumNodeType.REDUCER_GENERIC,
        "orchestrator": EnumNodeType.ORCHESTRATOR_GENERIC,
    }

    def __init__(
        self,
        constraint_validator: object | None = None,
        patch_validator: ContractPatchValidator | None = None,
        merge_validator: MergeValidator | None = None,
        expanded_validator: ExpandedContractValidator | None = None,
        event_emitter: ProtocolContractValidationEventEmitter | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """Initialize the pipeline with optional custom validators.

        Args:
            constraint_validator: Optional duck-typed validator for Phase 2.
                Must have a `validate(base, patch, merged)` method if provided.
                This is a seam for future SPI constraint validator integration.
            patch_validator: Custom Phase 1 validator. Defaults to
                ContractPatchValidator().
            merge_validator: Custom Phase 2 validator. Defaults to
                MergeValidator().
            expanded_validator: Custom Phase 3 validator. Defaults to
                ExpandedContractValidator().
            event_emitter: Optional event emitter for lifecycle events.
                When provided, the pipeline emits events at each stage
                (started, phase completed, passed/failed). This is useful
                for observability, auditing, and workflow tracking.
            correlation_id: Optional correlation ID for tracing. If provided,
                all emitted events will include this ID for request tracing
                across services. If not provided, a new UUID is generated
                per pipeline instance.

        Example with event emission:
            >>> emitter = MyEventEmitter(event_bus)
            >>> pipeline = ContractValidationPipeline(
            ...     event_emitter=emitter,
            ...     correlation_id=uuid4(),
            ... )
            >>> result = pipeline.validate_all(patch, profile_factory)
            # Events emitted: started -> merge_started -> merge_completed -> passed
        """
        self._constraint_validator = constraint_validator
        self._patch_validator = patch_validator or ContractPatchValidator()
        self._merge_validator = merge_validator or MergeValidator()
        self._expanded_validator = expanded_validator or ExpandedContractValidator()
        self._event_emitter = event_emitter
        self._correlation_id = correlation_id or uuid4()

        logger.debug(
            "ContractValidationPipeline initialized "
            f"(constraint_validator={'present' if constraint_validator else 'none'}, "
            f"event_emitter={'present' if event_emitter else 'none'}, "
            f"correlation_id={self._correlation_id})"
        )

    def _emit_event(self, event: ModelContractValidationEventBase) -> None:
        """Emit a contract validation lifecycle event.

        This helper handles event emission in a non-blocking way, suitable
        for both synchronous pipeline execution and async contexts.
        If no event emitter is configured, this method is a no-op.

        The method detects whether an event loop is already running:
        - If running (e.g., FastAPI endpoint): schedules emit as a task
        - If not running (sync context): uses asyncio.run()

        Args:
            event: The contract validation event to emit.

        Note:
            Event emission failures are logged but do not fail the pipeline.
            This ensures that event bus issues don't break validation.
        """
        if self._event_emitter is None:
            return

        try:
            # Handle both sync and async contexts
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                # Already in an async context - schedule as task (non-blocking)
                # Fire-and-forget: task runs independently, we don't await it
                _ = loop.create_task(self._event_emitter.emit(event))
            else:
                # Sync context - use asyncio.run
                asyncio.run(self._event_emitter.emit(event))

            # event_type is defined on subclasses, use getattr for type safety
            event_type = getattr(event, "event_type", type(event).__name__)
            logger.debug(f"Emitted event: {event_type}")
        except Exception as e:
            # boundary-ok: event emission should not fail the pipeline
            event_type = getattr(event, "event_type", type(event).__name__)
            logger.warning(
                f"Failed to emit event {event_type}: {e!s}. "
                "Continuing pipeline execution."
            )

    def validate_patch(self, patch: ModelContractPatch) -> ModelValidationResult[None]:
        """Validate a contract patch (Phase 1).

        Delegates to ContractPatchValidator to validate the patch structure
        and semantics before merge.

        Validation includes:
            - Duplicate detection within add lists
            - Behavior patch consistency
            - Identity field verification
            - Profile reference format checking

        Args:
            patch: The contract patch to validate.

        Returns:
            ModelValidationResult with:
                - is_valid: True if patch passes validation
                - issues: List of validation issues found
                - summary: Human-readable validation summary

        Example:
            >>> result = pipeline.validate_patch(patch)
            >>> if not result.is_valid:
            ...     print(f"Patch invalid: {result.summary}")
        """
        logger.debug(
            f"Phase 1 (PATCH): Starting validation for profile={patch.extends.profile}"
        )
        result = self._patch_validator.validate(patch)
        logger.debug(
            f"Phase 1 (PATCH): Completed - is_valid={result.is_valid}, "
            f"errors={result.error_level_count}, warnings={result.warning_count}"
        )
        return result

    def validate_merge(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
    ) -> ModelValidationResult[None]:
        """Validate a merge result (Phase 2).

        Delegates to MergeValidator and optionally calls the duck-typed
        constraint_validator if provided.

        Validation includes:
            - Placeholder value detection in critical fields
            - Required override verification
            - Dependency reference resolution
            - Handler name uniqueness
            - Capability consistency
            - Custom constraint validation (if constraint_validator provided)

        Duck-Typed Constraint Validator:
            If constraint_validator is provided and has a `validate` method,
            it will be called with (base, patch, merged) arguments. The result
            is merged with the MergeValidator result if it returns an object
            with `is_valid`, `issues`, `errors`, and `warnings` attributes.

        Args:
            base: The base contract from profile factory.
            patch: The patch that was applied.
            merged: The resulting merged contract.

        Returns:
            ModelValidationResult with:
                - is_valid: True if merge passes validation
                - issues: List of validation issues found
                - summary: Human-readable validation summary

        Example:
            >>> result = pipeline.validate_merge(base, patch, merged)
            >>> if not result.is_valid:
            ...     print(f"Merge invalid: {result.summary}")
        """
        logger.debug(f"Phase 2 (MERGE): Starting validation for contract={merged.name}")

        # Run primary merge validation
        result = self._merge_validator.validate(base, patch, merged)

        # Apply duck-typed constraint validator if provided
        if self._constraint_validator is not None:
            result = self._apply_constraint_validator(base, patch, merged, result)

        logger.debug(
            f"Phase 2 (MERGE): Completed - is_valid={result.is_valid}, "
            f"errors={result.error_level_count}, warnings={result.warning_count}"
        )
        return result

    def _apply_constraint_validator(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> ModelValidationResult[None]:
        """Apply duck-typed constraint validator and merge results.

        This method provides the seam for future SPI constraint validator
        integration. It checks if the constraint_validator has a `validate`
        method and calls it if present.

        The constraint validator result is merged if it returns an object
        compatible with ProtocolConstraintValidationResult (has is_valid,
        issues, errors, warnings attributes).

        Duck Typing:
            The hasattr checks enable duck typing without requiring explicit
            protocol inheritance. For type-safe implementations, use
            ProtocolConstraintValidator.

        Args:
            base: The base contract from profile factory.
            patch: The patch that was applied.
            merged: The merged contract to validate.
            result: The current validation result to merge into.

        Returns:
            Updated validation result with constraint validation merged.

        See Also:
            ProtocolConstraintValidator: Interface definition for validators.
            ProtocolConstraintValidationResult: Expected result interface.
        """
        # Guard for type narrowing (called only when not None, but pyright needs this)
        if self._constraint_validator is None:
            return result

        if not hasattr(self._constraint_validator, "validate"):
            logger.debug(
                "Constraint validator does not have 'validate' method, skipping"
            )
            return result

        logger.debug("Applying duck-typed constraint validator")

        try:
            # NOTE(OMN-1302): Duck-typed validator interface. Safe because validate() verified via hasattr() at runtime.
            constraint_result = self._constraint_validator.validate(  # type: ignore[attr-defined]
                base, patch, merged
            )

            # Merge results if the return value is compatible
            if hasattr(constraint_result, "is_valid"):
                # Update validity
                if not constraint_result.is_valid:
                    result.is_valid = False

                # Merge issues if available and not None
                if hasattr(constraint_result, "issues"):
                    if constraint_result.issues is not None:
                        result.issues.extend(constraint_result.issues)

                # Merge errors if available and not None
                if hasattr(constraint_result, "errors"):
                    if constraint_result.errors is not None:
                        result.errors.extend(constraint_result.errors)

                # Merge warnings if available and not None
                if hasattr(constraint_result, "warnings"):
                    if constraint_result.warnings is not None:
                        result.warnings.extend(constraint_result.warnings)

                logger.debug(
                    f"Constraint validator result merged: "
                    f"is_valid={constraint_result.is_valid}"
                )
            else:
                logger.warning(
                    "Constraint validator returned incompatible result type, "
                    "expected object with 'is_valid' attribute"
                )

        except (AttributeError, TypeError) as e:
            # fallback-ok: constraint validator may not be fully compatible
            logger.warning(
                f"Constraint validator call failed ({type(e).__name__}: {e})"
            )

        return result

    def validate_expanded(
        self,
        contract: ModelHandlerContract,
    ) -> ModelValidationResult[None]:
        """Validate a fully expanded contract (Phase 3).

        Delegates to ExpandedContractValidator to validate the contract
        for runtime correctness.

        Validation includes:
            - Handler ID format validation
            - Input/output model reference validation
            - Version format validation
            - Execution graph integrity (cycles and orphans)
            - Event routing correctness
            - Capability input format validation
            - Handler kind consistency

        Args:
            contract: The fully expanded contract to validate.

        Returns:
            ModelValidationResult with:
                - is_valid: True if contract passes validation
                - issues: List of validation issues found
                - summary: Human-readable validation summary

        Example:
            >>> result = pipeline.validate_expanded(contract)
            >>> if not result.is_valid:
            ...     print(f"Contract invalid: {result.summary}")
        """
        logger.debug(
            f"Phase 3 (EXPANDED): Starting validation for handler_id={contract.handler_id}"
        )
        result = self._expanded_validator.validate(contract)
        logger.debug(
            f"Phase 3 (EXPANDED): Completed - is_valid={result.is_valid}, "
            f"errors={result.error_level_count}, warnings={result.warning_count}"
        )
        return result

    def _perform_merge_operation(
        self,
        patch: ModelContractPatch,
        profile_factory: ProtocolContractProfileFactory,
    ) -> tuple[ModelHandlerContract, ModelHandlerContract]:
        """Perform the merge operation and return merged and base contracts.

        This method encapsulates the merge logic including:
            - Creating the merge engine
            - Performing the merge operation
            - Determining the node type from profile name
            - Resolving the base contract from the profile factory

        Args:
            patch: The contract patch to merge.
            profile_factory: Factory for resolving base contracts from profiles.

        Returns:
            Tuple of (merged_contract, base_contract).

        Raises:
            Exception: If merge operation fails for any reason.
                The caller should catch and handle appropriately.
        """
        # Import here to avoid circular import at module level
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        merge_engine = ContractMergeEngine(profile_factory)
        merged_contract = merge_engine.merge(patch)

        # Determine node type from profile name prefix
        profile_name = patch.extends.profile.lower()
        node_type = EnumNodeType.COMPUTE_GENERIC  # default

        for prefix, ntype in self._PREFIX_TO_NODE_TYPE_MAP.items():
            if profile_name.startswith(prefix):
                node_type = ntype
                break

        base_contract = profile_factory.get_profile(
            node_type=node_type,
            profile=patch.extends.profile,
            version=patch.extends.version,
        )

        return merged_contract, cast(ModelHandlerContract, base_contract)

    def validate_all(
        self,
        patch: ModelContractPatch,
        profile_factory: ProtocolContractProfileFactory,
    ) -> ModelExpandedContractResult:
        """Run all validation phases and return expanded contract.

        Executes all three validation phases sequentially:
            1. PATCH: Validate the patch
            2. MERGE: Merge patch with base and validate result
            3. EXPANDED: Validate the expanded contract

        The pipeline stops on the first phase that produces critical errors.
        All validation results are preserved in the return value.

        Args:
            patch: The contract patch to validate and expand.
            profile_factory: Factory for resolving base contracts from profiles.
                Must implement ProtocolContractProfileFactory protocol.

        Returns:
            ModelExpandedContractResult with:
                - success: True if all phases passed
                - contract: The expanded contract (if success=True)
                - validation_results: Results for each executed phase
                - errors: Aggregated error messages
                - phase_failed: The phase where validation failed (if any)

        Example:
            >>> result = pipeline.validate_all(patch, profile_factory)
            >>> if result.success:
            ...     contract = result.contract
            ...     print(f"Validated: {contract.name}")
            ... else:
            ...     print(f"Failed at {result.phase_failed}: {result.errors}")
        """
        logger.info(
            f"Pipeline: Starting validation for profile={patch.extends.profile}"
        )

        # Initialize pipeline tracking
        result = ModelExpandedContractResult()
        all_errors: list[str] = []
        run_id = uuid4()  # Links all events in this validation lifecycle
        start_time = time.monotonic()
        contract_name = patch.extends.profile  # Use profile as contract name initially

        # Emit validation started event
        started_event = ModelContractValidationStartedEvent.create(
            contract_name=contract_name,
            run_id=run_id,
            context=ModelContractValidationContext(),
            correlation_id=self._correlation_id,
        )
        self._emit_event(started_event)

        # =====================================================================
        # Phase 1: PATCH Validation
        # =====================================================================
        logger.debug("Pipeline: Executing Phase 1 (PATCH)")
        patch_result = self.validate_patch(patch)
        result.validation_results[EnumValidationPhase.PATCH.value] = patch_result

        # Collect errors
        all_errors.extend(patch_result.errors)

        # Check for critical errors
        if not patch_result.is_valid:
            logger.info(
                f"Pipeline: Failed at Phase 1 (PATCH) - {patch_result.error_level_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.PATCH

            # Emit validation failed event
            duration_ms = int((time.monotonic() - start_time) * 1000)
            failed_event = ModelContractValidationFailedEvent.create(
                contract_name=contract_name,
                run_id=run_id,
                error_count=patch_result.error_level_count,
                first_error_code="PATCH_VALIDATION_FAILED",
                duration_ms=duration_ms,
                violations=all_errors[:100],  # Bounded to MAX_VIOLATION_ENTRIES
                correlation_id=self._correlation_id,
            )
            self._emit_event(failed_event)
            return result

        # =====================================================================
        # Merge Operation
        # =====================================================================
        logger.debug("Pipeline: Performing merge operation")

        # Emit merge started event
        merge_start_time = time.monotonic()
        merge_started_event = ModelContractMergeStartedEvent.create(
            contract_name=contract_name,
            run_id=run_id,
            profile_names=[patch.extends.profile],
            correlation_id=self._correlation_id,
        )
        self._emit_event(merge_started_event)

        try:
            merged_contract, base_contract = self._perform_merge_operation(
                patch, profile_factory
            )

            # Emit merge completed event
            merge_duration_ms = int((time.monotonic() - merge_start_time) * 1000)
            merge_completed_event = ModelContractMergeCompletedEvent.create(
                contract_name=contract_name,
                run_id=run_id,
                effective_contract_name=merged_contract.name,
                duration_ms=merge_duration_ms,
                defaults_applied=True,
                correlation_id=self._correlation_id,
            )
            self._emit_event(merge_completed_event)

            # Update contract_name to use the merged contract name
            contract_name = merged_contract.name

        except Exception as e:
            # fallback-ok: merge can fail for many reasons, return error result
            logger.exception(f"Pipeline: Merge operation failed - {e}")
            all_errors.append(f"Merge operation failed: {e}")
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.MERGE

            # Emit validation failed event for merge failure
            duration_ms = int((time.monotonic() - start_time) * 1000)
            failed_event = ModelContractValidationFailedEvent.create(
                contract_name=contract_name,
                run_id=run_id,
                error_count=1,
                first_error_code="MERGE_OPERATION_FAILED",
                duration_ms=duration_ms,
                violations=[str(e)],
                correlation_id=self._correlation_id,
            )
            self._emit_event(failed_event)
            return result

        # =====================================================================
        # Phase 2: MERGE Validation
        # =====================================================================
        logger.debug("Pipeline: Executing Phase 2 (MERGE)")

        # Duck-typing check for runtime safety. The profile factory may return
        # contracts that don't have all ModelHandlerContract attributes.
        # This check avoids AttributeError at runtime while keeping type safety.
        merge_result: ModelValidationResult[None]
        if hasattr(base_contract, "handler_id") and hasattr(
            base_contract, "descriptor"
        ):
            # Base contract has required attributes for detailed merge validation
            merge_result = self.validate_merge(base_contract, patch, merged_contract)
        else:
            # Base contract is not a ModelHandlerContract - skip detailed validation
            logger.warning(
                "Base contract lacks handler_id/descriptor, "
                "skipping detailed merge validation"
            )
            merge_result = ModelValidationResult(
                is_valid=True,
                summary="Merge validation skipped (base contract type mismatch)",
            )

        result.validation_results[EnumValidationPhase.MERGE.value] = merge_result

        # Collect errors
        all_errors.extend(merge_result.errors)

        # Check for critical errors
        if not merge_result.is_valid:
            logger.info(
                f"Pipeline: Failed at Phase 2 (MERGE) - {merge_result.error_level_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.MERGE

            # Emit validation failed event
            duration_ms = int((time.monotonic() - start_time) * 1000)
            failed_event = ModelContractValidationFailedEvent.create(
                contract_name=contract_name,
                run_id=run_id,
                error_count=merge_result.error_level_count,
                first_error_code="MERGE_VALIDATION_FAILED",
                duration_ms=duration_ms,
                violations=all_errors[:100],
                correlation_id=self._correlation_id,
            )
            self._emit_event(failed_event)
            return result

        # =====================================================================
        # Phase 3: EXPANDED Validation
        # =====================================================================
        logger.debug("Pipeline: Executing Phase 3 (EXPANDED)")
        expanded_result = self.validate_expanded(merged_contract)
        result.validation_results[EnumValidationPhase.EXPANDED.value] = expanded_result

        # Collect errors
        all_errors.extend(expanded_result.errors)

        # Check for critical errors
        if not expanded_result.is_valid:
            logger.info(
                f"Pipeline: Failed at Phase 3 (EXPANDED) - {expanded_result.error_level_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.EXPANDED

            # Emit validation failed event
            duration_ms = int((time.monotonic() - start_time) * 1000)
            failed_event = ModelContractValidationFailedEvent.create(
                contract_name=contract_name,
                run_id=run_id,
                error_count=expanded_result.error_level_count,
                first_error_code="EXPANDED_VALIDATION_FAILED",
                duration_ms=duration_ms,
                violations=all_errors[:100],
                correlation_id=self._correlation_id,
            )
            self._emit_event(failed_event)
            return result

        # =====================================================================
        # Success: All Phases Passed
        # =====================================================================
        logger.info(f"Pipeline: All phases passed for contract={merged_contract.name}")
        result.success = True
        result.contract = merged_contract
        result.errors = all_errors  # May contain warnings from earlier phases

        # Emit validation passed event
        duration_ms = int((time.monotonic() - start_time) * 1000)
        total_warnings = (
            patch_result.warning_count
            + merge_result.warning_count
            + expanded_result.warning_count
        )
        # checks_run represents the number of validation phases executed (PATCH, MERGE, EXPANDED)
        # Not the number of issues found (which would be misleading for a "passed" event)
        passed_event = ModelContractValidationPassedEvent.create(
            contract_name=contract_name,
            run_id=run_id,
            duration_ms=duration_ms,
            warnings_count=total_warnings,
            checks_run=3,
            correlation_id=self._correlation_id,
        )
        self._emit_event(passed_event)

        return result
