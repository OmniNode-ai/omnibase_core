# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.validation.model_expanded_contract_result import (
    ExpandedContractResult,
)
from omnibase_core.protocols.validation.protocol_contract_validation_pipeline import (
    ProtocolContractValidationPipeline,
)
from omnibase_core.validation.contract_patch_validator import ContractPatchValidator
from omnibase_core.validation.phases.expanded_validator import ExpandedContractValidator
from omnibase_core.validation.phases.merge_validator import MergeValidator

if TYPE_CHECKING:
    from omnibase_core.protocols.protocol_contract_profile_factory import (
        ProtocolContractProfileFactory,
    )

__all__ = [
    "ContractValidationPipeline",
    "ExpandedContractResult",
    "ProtocolContractValidationPipeline",
]

# Configure logger for this module
logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Implementation
# =============================================================================


class ContractValidationPipeline:
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
        ...
        >>> # With custom constraint validator
        >>> constraint_validator = MyConstraintValidator()
        >>> pipeline = ContractValidationPipeline(
        ...     constraint_validator=constraint_validator
        ... )
        >>> result = pipeline.validate_all(patch, profile_factory)

    Attributes:
        _constraint_validator: Optional duck-typed validator for Phase 2.
        _patch_validator: Phase 1 validator (ContractPatchValidator).
        _merge_validator: Phase 2 validator (MergeValidator).
        _expanded_validator: Phase 3 validator (ExpandedContractValidator).

    See Also:
        - ContractPatchValidator: Phase 1 validation
        - MergeValidator: Phase 2 validation
        - ExpandedContractValidator: Phase 3 validation
        - ContractMergeEngine: Merge operations
    """

    def __init__(
        self,
        constraint_validator: object | None = None,
        patch_validator: ContractPatchValidator | None = None,
        merge_validator: MergeValidator | None = None,
        expanded_validator: ExpandedContractValidator | None = None,
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
        """
        self._constraint_validator = constraint_validator
        self._patch_validator = patch_validator or ContractPatchValidator()
        self._merge_validator = merge_validator or MergeValidator()
        self._expanded_validator = expanded_validator or ExpandedContractValidator()

        logger.debug(
            "ContractValidationPipeline initialized "
            f"(constraint_validator={'present' if constraint_validator else 'none'})"
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
            f"errors={result.error_count}, warnings={result.warning_count}"
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
            f"errors={result.error_count}, warnings={result.warning_count}"
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
        compatible with ModelValidationResult (has is_valid, issues, errors,
        warnings attributes).

        Args:
            base: The base contract from profile factory.
            patch: The patch that was applied.
            merged: The merged contract to validate.
            result: The current validation result to merge into.

        Returns:
            Updated validation result with constraint validation merged.
        """
        if not hasattr(self._constraint_validator, "validate"):
            logger.debug(
                "Constraint validator does not have 'validate' method, skipping"
            )
            return result

        logger.debug("Applying duck-typed constraint validator")

        try:
            # Call the duck-typed validator
            constraint_result = self._constraint_validator.validate(  # type: ignore[union-attr]
                base, patch, merged
            )

            # Merge results if the return value is compatible
            if hasattr(constraint_result, "is_valid"):
                # Update validity
                if not constraint_result.is_valid:
                    result.is_valid = False

                # Merge issues if available
                if hasattr(constraint_result, "issues"):
                    result.issues.extend(constraint_result.issues)

                # Merge errors if available
                if hasattr(constraint_result, "errors"):
                    result.errors.extend(constraint_result.errors)

                # Merge warnings if available
                if hasattr(constraint_result, "warnings"):
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
                f"Constraint validator call failed (duck-typing mismatch): {e}"
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
            f"errors={result.error_count}, warnings={result.warning_count}"
        )
        return result

    def validate_all(
        self,
        patch: ModelContractPatch,
        profile_factory: ProtocolContractProfileFactory,
    ) -> ExpandedContractResult:
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
            ExpandedContractResult with:
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

        result = ExpandedContractResult()
        all_errors: list[str] = []

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
                f"Pipeline: Failed at Phase 1 (PATCH) - {patch_result.error_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.PATCH
            return result

        # =====================================================================
        # Merge Operation
        # =====================================================================
        logger.debug("Pipeline: Performing merge operation")
        try:
            # Import here to avoid circular import at module level
            from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

            merge_engine = ContractMergeEngine(profile_factory)
            merged_contract = merge_engine.merge(patch)

            # Get base contract for merge validation
            from omnibase_core.enums import EnumNodeType

            # Determine node type from profile name
            profile_name = patch.extends.profile.lower()
            node_type = EnumNodeType.COMPUTE_GENERIC  # default
            prefix_map = {
                "compute": EnumNodeType.COMPUTE_GENERIC,
                "effect": EnumNodeType.EFFECT_GENERIC,
                "reducer": EnumNodeType.REDUCER_GENERIC,
                "orchestrator": EnumNodeType.ORCHESTRATOR_GENERIC,
            }
            for prefix, ntype in prefix_map.items():
                if profile_name.startswith(prefix):
                    node_type = ntype
                    break

            base_contract = profile_factory.get_profile(
                node_type=node_type,
                profile=patch.extends.profile,
                version=patch.extends.version,
            )

        except (
            Exception
        ) as e:  # fallback-ok: merge can fail for many reasons, return error result
            logger.exception(f"Pipeline: Merge operation failed - {e}")
            all_errors.append(f"Merge operation failed: {e}")
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.MERGE
            return result

        # =====================================================================
        # Phase 2: MERGE Validation
        # =====================================================================
        logger.debug("Pipeline: Executing Phase 2 (MERGE)")

        # The factory returns ModelContractBase but merge validator expects
        # ModelHandlerContract. Use duck-typing via hasattr checks to determine
        # if we can perform detailed merge validation.
        #
        # Duck-typing approach avoids isinstance issues where mypy incorrectly
        # detects unreachable code due to incompatible method signatures between
        # ModelContractBase and ModelHandlerContract.
        merge_result: ModelValidationResult[None]
        if hasattr(base_contract, "handler_id") and hasattr(
            base_contract, "descriptor"
        ):
            # Base contract has the required attributes for detailed merge validation
            # Safe to cast for type checker since we verified attributes
            from typing import cast

            base_as_handler = cast(ModelHandlerContract, base_contract)
            merge_result = self.validate_merge(base_as_handler, patch, merged_contract)
        else:
            # Base contract is not a ModelHandlerContract - skip detailed validation
            logger.warning(
                "Base contract lacks handler_id/descriptor, skipping detailed merge validation"
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
                f"Pipeline: Failed at Phase 2 (MERGE) - {merge_result.error_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.MERGE
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
                f"Pipeline: Failed at Phase 3 (EXPANDED) - {expanded_result.error_count} errors"
            )
            result.errors = all_errors
            result.phase_failed = EnumValidationPhase.EXPANDED
            return result

        # =====================================================================
        # Success: All Phases Passed
        # =====================================================================
        logger.info(f"Pipeline: All phases passed for contract={merged_contract.name}")
        result.success = True
        result.contract = merged_contract
        result.errors = all_errors  # May contain warnings from earlier phases

        return result
