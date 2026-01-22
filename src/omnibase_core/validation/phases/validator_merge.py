"""
Merge Validator for Phase 2 Contract Validation.

Validates contracts AFTER merge but BEFORE expansion. This phase ensures that
the merge operation produced a valid intermediate contract that is ready for
full expansion and runtime use.

Validation Philosophy:
    - Structural: Validates merge result shape and completeness
    - Semantic: Validates internal consistency after merge
    - NOT Resolutive: Does not resolve external references or profiles

Logging Conventions:
    - DEBUG: Detailed trace information (validation steps, field checks)
    - INFO: High-level operation summaries (validation started/passed/failed)
    - WARNING: Recoverable issues that don't fail validation

Error Code Conventions:
    Error codes in this module use the CONTRACT_VALIDATION_MERGE_* prefix for
    consistent categorization per OMN-1128. All codes are defined in
    EnumContractValidationErrorCode:
    - CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING: Required field not overridden
    - CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED: Placeholder value not replaced
    - CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED: Dependency not found
    - CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED: Merge conflict (e.g., name uniqueness)

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractPatchValidator: Phase 1 validation
    - ContractMergeEngine: Merge operations this validates

.. versionadded:: 0.4.1
"""

import logging
import re
from collections.abc import Sequence

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract

__all__ = [
    "MergeValidator",
]

# Configure logger for this module
logger = logging.getLogger(__name__)

# =============================================================================
# Placeholder Detection Patterns
# =============================================================================
#
# These patterns identify placeholder values that should be replaced during
# contract authoring. Placeholder values in merged contracts indicate incomplete
# configuration that would fail at runtime.
#
# Pattern Categories:
#   - TODO markers: TODO, TBD, FIXME
#   - Placeholder markers: PLACEHOLDER, REPLACE_ME, CHANGE_ME
#   - Template markers: ${VAR_NAME}, {{variable}}, <PLACEHOLDER>
#   - Empty/default markers: Empty strings, "default", "undefined"
# =============================================================================

# Exact match placeholders (case-insensitive)
#
# NOTE: These patterns match ONLY when the entire normalized value equals the
# pattern exactly (case-insensitive). Substring matching is NOT performed.
#
# For example:
#   - "test" matches: "test", "TEST", "Test"
#   - "test" does NOT match: "test_handler", "my_test", "testing"
#
# This means a handler named "test_user_handler" will NOT trigger a false
# positive, but a field with just "test" as its value will be flagged as a
# placeholder (which is appropriate for critical fields like handler_id, name,
# version, input_model, and output_model in production contracts).
_PLACEHOLDER_EXACT_PATTERNS: frozenset[str] = frozenset(
    {
        "todo",
        "tbd",
        "fixme",
        "placeholder",
        "replace_me",
        "change_me",
        "undefined",
        "default",
        "example",
        "sample",
        # Special case: "test" is included because a critical field (handler_id,
        # name, version, input_model, output_model) with just "test" as its value
        # is likely a placeholder in production contracts. Handler names like
        # "test_user_handler" will NOT match because this is exact matching, not
        # substring matching.
        "test",
        "xxx",
        "???",
        "...",
    }
)

# Regex patterns for template-style placeholders
_PLACEHOLDER_REGEX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$\{[^}]+\}"),  # ${VAR_NAME} style
    re.compile(r"\{\{[^}]+\}\}"),  # {{variable}} style (Jinja/Mustache)
    re.compile(r"<[A-Z_]+>"),  # <PLACEHOLDER> style
    re.compile(r"^\s*TODO\s*:", re.IGNORECASE),  # "TODO: description" style
)

# Critical fields that must not contain placeholder values
_CRITICAL_FIELDS: frozenset[str] = frozenset(
    {
        "handler_id",
        "name",
        "contract_version",
        "input_model",
        "output_model",
    }
)


def _is_placeholder_value(  # stub-ok: docstring describes detection patterns
    value: str,
) -> bool:
    """
    Check if a string value is a placeholder that should be replaced.

    Detection covers:
        - Exact match placeholders (TODO, PLACEHOLDER, etc.)
        - Template-style placeholders (${VAR}, {{var}}, <PLACEHOLDER>)
        - Whitespace-only or empty strings

    Args:
        value: The string value to check.

    Returns:
        True if the value appears to be a placeholder, False otherwise.
    """
    if not value or not value.strip():
        return True

    # Check exact matches (case-insensitive)
    normalized = value.strip().lower()
    if normalized in _PLACEHOLDER_EXACT_PATTERNS:
        return True

    # Check regex patterns
    for pattern in _PLACEHOLDER_REGEX_PATTERNS:
        if pattern.search(value):
            return True

    return False


class MergeValidator:
    """
    Validates merged contracts before expansion (Phase 2).

    This validator runs AFTER the merge operation completes but BEFORE the
    contract is expanded for runtime use. It ensures the merge produced a
    valid intermediate contract.

    Validation Checks:
        - Required overrides present: Placeholder values in base were overridden
        - Placeholder values rejected: No TODO/PLACEHOLDER markers in critical fields
        - Dependency references resolve: All dependency names exist in merged contract
        - Handler name uniqueness: No duplicate handler names after merge
        - Capability consistency: Input/output capabilities are consistent

    Thread Safety:
        This class is stateless and thread-safe. Each call to validate()
        operates independently without shared mutable state.

    Example:
        >>> validator = MergeValidator()
        >>> result = validator.validate(base, patch, merged)
        >>> if result.is_valid:
        ...     # Proceed to expansion phase
        ...     expanded = expander.expand(merged)
        ... else:
        ...     for issue in result.issues:
        ...         print(f"{issue.severity}: {issue.message}")

    See Also:
        - ContractPatchValidator: Phase 1 validation
        - ContractMergeEngine: Produces merged contracts
        - EnumContractValidationErrorCode: Error codes used
    """

    def validate(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
    ) -> ModelValidationResult[None]:
        """
        Validate merge result before expansion.

        Performs all Phase 2 validation checks on the merged contract,
        comparing it against the original base and patch to ensure the
        merge operation completed correctly.

        Validation includes:
            - Placeholder value detection in critical fields
            - Dependency reference resolution
            - Handler name uniqueness
            - Capability input/output consistency

        Args:
            base: Original base contract from profile factory.
            patch: The patch that was applied to the base.
            merged: The resulting merged contract to validate.

        Returns:
            ModelValidationResult with:
                - is_valid: True if all checks pass
                - issues: List of validation issues (errors, warnings, info)
                - summary: Human-readable validation summary

        Example:
            >>> validator = MergeValidator()
            >>> result = validator.validate(base, patch, merged)
            >>> if not result.is_valid:
            ...     for error in result.errors:
            ...         print(f"Error: {error}")
        """
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Merge validation started",
        )

        logger.debug(
            f"Starting merge validation for merged contract: "
            f"name={merged.name}, handler_id={merged.handler_id}"
        )

        # Run validation checks
        self._validate_placeholder_values(merged, result)
        self._validate_required_overrides(base, patch, merged, result)
        self._validate_dependency_references(base, patch, merged, result)
        self._validate_handler_name_uniqueness(base, patch, result)
        self._validate_capability_consistency(merged, result)

        # Update summary based on results
        if result.is_valid:
            result.summary = "Merge validation passed"
            logger.info(
                f"Merge validation passed for {merged.name} "
                f"(warnings={result.warning_count})"
            )
        else:
            result.summary = (
                f"Merge validation failed with {result.error_level_count} errors"
            )
            logger.info(
                f"Merge validation failed for {merged.name}: "
                f"{result.error_level_count} errors, {result.warning_count} warnings"
            )

        return result

    # =========================================================================
    # Private Validation Methods
    # =========================================================================

    def _validate_placeholder_values(  # stub-ok: docstring describes detection patterns
        self,
        merged: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Detect and reject placeholder values in critical fields.

        Placeholder values like TODO, PLACEHOLDER, ${VAR}, or empty strings
        in critical fields indicate incomplete configuration that would fail
        at runtime.

        Critical fields checked:
            - handler_id
            - name
            - contract_version
            - input_model
            - output_model

        Args:
            merged: The merged contract to check.
            result: The validation result to append issues to.
        """
        logger.debug("Checking for placeholder values in critical fields")

        # Build field->value mapping for critical fields
        # Note: contract_version is ModelSemVer, convert to string for placeholder check
        field_values: dict[str, str] = {
            "handler_id": merged.handler_id,
            "name": merged.name,
            "contract_version": str(merged.contract_version),
            "input_model": merged.input_model,
            "output_model": merged.output_model,
        }

        # Check each critical field
        for field_name, value in field_values.items():
            if _is_placeholder_value(value):
                logger.debug(f"Placeholder detected in {field_name}: {value!r}")
                result.add_error(
                    f"Placeholder value detected in '{field_name}': {value!r}. "
                    "All placeholder values must be replaced before expansion.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED.value,
                    suggestion=f"Provide a valid value for '{field_name}' in the contract patch",
                )

        # Also check description if present (warning, not error)
        if merged.description and _is_placeholder_value(merged.description):
            logger.debug(f"Placeholder detected in description: {merged.description!r}")
            result.add_warning(
                f"Placeholder value detected in 'description': {merged.description!r}. "
                "Consider providing a meaningful description.",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED.value,
                suggestion="Provide a meaningful description in the contract patch",
            )

    def _validate_required_overrides(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Verify that required placeholder values in base were overridden.

        If the base contract has placeholder values that MUST be overridden
        by any patch using it, verify the patch provided these values.

        This check detects when a base contract's placeholder "leaked" into
        the merged result because the patch failed to provide an override.

        Args:
            base: Original base contract with potential placeholders.
            patch: The patch that should have provided overrides.
            merged: The merged result to verify.
            result: The validation result to append issues to.
        """
        logger.debug("Checking for required overrides from base placeholders")

        # Check if base had placeholder values that should have been overridden
        base_field_values: dict[str, str] = {
            "name": base.name,
            "input_model": base.input_model,
            "output_model": base.output_model,
        }

        for field_name, base_value in base_field_values.items():
            if _is_placeholder_value(base_value):
                # Base had a placeholder - check if merged still has it
                merged_value = getattr(merged, field_name, None)
                if merged_value == base_value:
                    # Placeholder was not overridden
                    logger.debug(
                        f"Required override missing for {field_name}: "
                        f"base={base_value!r}, merged={merged_value!r}"
                    )
                    result.add_error(
                        f"Required override missing for '{field_name}'. "
                        f"Base contract has placeholder '{base_value}' that "
                        "must be overridden by the patch.",
                        code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING.value,
                        suggestion=f"Add '{field_name}' override in your contract patch",
                    )

    def _validate_dependency_references(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        merged: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Verify that dependency names in patch resolve correctly.

        Dependencies being added by the patch should not reference handlers
        that don't exist in either the base contract or the patch itself.
        This prevents orphaned dependency references.

        Note:
            This is a structural check only. Full dependency resolution
            (verifying the dependency handler actually exists in the registry)
            is deferred to Phase 3 (expanded validation).

        Args:
            base: Original base contract with existing handlers.
            patch: The patch with potential new dependencies.
            merged: The merged result for reference.
            result: The validation result to append issues to.
        """
        logger.debug("Checking dependency reference resolution")

        # Skip if no dependencies being added
        if not patch.dependencies__add:
            logger.debug("No dependencies being added, skipping reference check")
            return

        # Build set of known handler names from base and patch
        known_handlers: set[str] = set()

        # Add handler names from base's capability inputs.
        # These capability input aliases are handler dependencies.
        for cap_dep in base.capability_inputs:
            known_handlers.add(cap_dep.alias)

        # Add handler names from patch's handlers__add
        if patch.handlers__add:
            for handler_spec in patch.handlers__add:
                known_handlers.add(handler_spec.name)

        # Check each dependency being added
        for dep in patch.dependencies__add:
            # Dependency names can reference handlers or external capabilities
            # For now, we just warn if the name looks like it should reference a handler
            # but doesn't exist in known handlers
            #
            # Handler reference extraction:
            #   - "handler.<ref>" → extract everything after "handler." prefix
            #   - "node.<ref>" → extract everything after "node." prefix
            #
            # This avoids false positives from extracting only the last segment.
            # For example, "node.user.compute" extracts "user.compute" rather than
            # just "compute", which could incorrectly match an unrelated handler.
            handler_ref: str | None = None
            if dep.name.startswith("handler."):
                # Extract portion after "handler." prefix
                # e.g., "handler.my_handler" → "my_handler"
                # e.g., "handler.module.handler_name" → "module.handler_name"
                handler_ref = dep.name[len("handler.") :]
            elif dep.name.startswith("node."):
                # Extract portion after "node." prefix
                # e.g., "node.user.compute" → "user.compute"
                handler_ref = dep.name[len("node.") :]

            if handler_ref is not None and handler_ref not in known_handlers:
                logger.debug(f"Potential unresolved dependency reference: {dep.name}")
                result.add_issue(
                    severity=EnumSeverity.WARNING,
                    message=(
                        f"Dependency '{dep.name}' references a handler that "
                        "may not exist in this contract. Verify the handler "
                        "exists in the base contract or is being added by the patch."
                    ),
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED.value,
                    suggestion=(
                        f"Add handler '{handler_ref}' to handlers__add or "
                        "verify it exists in the base contract"
                    ),
                )

    def _validate_handler_name_uniqueness(
        self,
        base: ModelHandlerContract,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Ensure no duplicate handler names after merge.

        If handlers are being added by the patch, verify none of them
        conflict with existing handler names in the base contract.

        Args:
            base: Original base contract with existing handlers.
            patch: The patch with potential new handlers.
            result: The validation result to append issues to.
        """
        logger.debug("Checking handler name uniqueness")

        # Skip if no handlers being added
        if not patch.handlers__add:
            logger.debug("No handlers being added, skipping uniqueness check")
            return

        # Build set of existing handler aliases from base capability inputs
        # (capability_inputs reference handlers by alias)
        existing_names: set[str] = {cap.alias for cap in base.capability_inputs}

        # Check each handler being added
        add_handler_names: list[str] = [h.name for h in patch.handlers__add]

        # Check for duplicates within the add list itself
        seen_names: set[str] = set()
        for name in add_handler_names:
            if name in seen_names:
                logger.debug(f"Duplicate handler in patch: {name}")
                result.add_error(
                    f"Duplicate handler name '{name}' in handlers__add list.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value,
                    suggestion="Remove duplicate handler from handlers__add",
                )
            seen_names.add(name)

        # Check for conflicts with existing handlers
        for name in add_handler_names:
            if name in existing_names:
                # Check if it's also being removed (that's allowed)
                if patch.handlers__remove and name in patch.handlers__remove:
                    logger.debug(
                        f"Handler '{name}' conflicts but is also in remove list - OK"
                    )
                    continue

                logger.debug(f"Handler name conflict with base: {name}")
                result.add_error(
                    f"Handler name '{name}' conflicts with existing handler in "
                    "base contract. Use a different name or remove the existing "
                    "handler first.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value,
                    suggestion=(
                        f"Rename the handler or add '{name}' to handlers__remove "
                        "before adding a replacement"
                    ),
                )

    def _validate_capability_consistency(
        self,
        merged: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Verify capability inputs/outputs are consistent after merge.

        Checks:
            - No duplicate capability input aliases
            - No duplicate capability output names
            - Capability input aliases don't conflict with output names

        Args:
            merged: The merged contract to validate.
            result: The validation result to append issues to.
        """
        logger.debug("Checking capability consistency")

        # Check for duplicate capability input aliases
        input_aliases: list[str] = [cap.alias for cap in merged.capability_inputs]
        self._check_for_duplicates(
            items=input_aliases,
            field_name="capability_inputs",
            item_type="alias",
            result=result,
        )

        # Check for duplicate capability output names
        output_names: list[str] = list(merged.capability_outputs)
        self._check_for_duplicates(
            items=output_names,
            field_name="capability_outputs",
            item_type="name",
            result=result,
        )

        # Check for alias/output name conflicts (warning only)
        input_alias_set = set(input_aliases)
        output_name_set = set(output_names)
        conflicts = input_alias_set & output_name_set
        if conflicts:
            sorted_conflicts = sorted(conflicts)
            logger.debug(f"Capability input/output name conflicts: {sorted_conflicts}")
            result.add_warning(
                f"Capability input aliases conflict with output names: {sorted_conflicts}. "
                "This may cause confusion in capability resolution.",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value,
                suggestion="Use distinct names for capability inputs and outputs",
            )

    def _check_for_duplicates(
        self,
        items: Sequence[str],
        field_name: str,
        item_type: str,
        result: ModelValidationResult[None],
    ) -> None:
        """
        Check for duplicate items in a sequence and report errors.

        Complexity: O(n) where n = len(items).
            - Single pass through items: O(n)
            - Set membership check and insertion: O(1) amortized
            - Duplicates are collected only on collision (no extra iteration)

        Args:
            items: Sequence of string items to check.
            field_name: Name of the field for error messages.
            item_type: Type of item (e.g., "alias", "name") for messages.
            result: The validation result to append issues to.
        """
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in items:
            if item in seen:
                duplicates.add(item)
            seen.add(item)

        if duplicates:
            sorted_duplicates = sorted(duplicates)
            logger.debug(f"Duplicate {item_type}s in {field_name}: {sorted_duplicates}")
            result.add_error(
                f"Duplicate {item_type}(s) in {field_name}: {sorted_duplicates}",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value,
                suggestion=f"Remove duplicate {item_type}s from {field_name}",
            )
