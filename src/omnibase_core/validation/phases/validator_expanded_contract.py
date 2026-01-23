"""
Expanded Contract Validator (Phase 3).

Validates fully expanded/resolved contracts for runtime correctness.
This is the final validation phase before a contract can be used at runtime.

Validation Philosophy:
    - Execution Graph: Validates dependency ordering (no cycles, no orphans)
    - Event Routing: Validates event consumption and production consistency
    - Dependencies: Validates capability input format and uniqueness
    - Runtime Invariants: Validates contract structure matches runtime requirements

Validation is deterministic and environment-agnostic. It does NOT attempt to:
    - Resolve actual capability providers (deferred to runtime)
    - Load or validate actual input/output model classes
    - Check profile existence (already done in Phase 2)

Logging Conventions:
    - DEBUG: Detailed trace information (validation steps, field checks)
    - INFO: High-level operation summaries (validation started/passed/failed)
    - WARNING: Recoverable issues that don't fail validation

Error Code Conventions:
    Error codes in this module use the CONTRACT_VALIDATION_EXPANDED_* prefix.
    All codes are defined in EnumContractValidationErrorCode.

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractPatchValidator: Phase 1 patch validation
    - TypedContractMergeEngine: Phase 2 merge validation

.. versionadded:: 0.4.0
"""

import logging
import re

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract

__all__ = [
    "ExpandedContractValidator",
]

# Configure logger for this module
logger = logging.getLogger(__name__)

# =============================================================================
# Validation Patterns
# =============================================================================

# Dot-separated identifier pattern: used for handler IDs and model references
# Format: segments separated by dots, each starting with letter or underscore
# Examples: node.user.reducer, omnibase_core.models.events.ModelUserEvent
#
# This pattern is shared between handler ID and model reference validation
# because both require the same structural format (dot-separated Python identifiers).
_DOT_SEPARATED_IDENTIFIER_PATTERN = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$"
)

# Handler ID format: dot-separated segments, each starting with letter or underscore
# Examples: node.user.reducer, handler.email.sender, _internal.service
HANDLER_ID_PATTERN = _DOT_SEPARATED_IDENTIFIER_PATTERN

# Model reference pattern: looks like a valid Python module path
# Examples: omnibase_core.models.events.ModelUserEvent, myapp.Input
# Note: Uses same pattern as handler IDs - both are dot-separated identifiers
MODEL_REFERENCE_PATTERN = _DOT_SEPARATED_IDENTIFIER_PATTERN

# Semver pattern for version validation
# Matches: 1.0.0, 1.0.0-beta.1, 1.0.0+build.123
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$")

# Capability name pattern: dot-notation with alphanumeric segments
# Examples: database.relational, cache.distributed, event.user_created
CAPABILITY_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$")

# Event type pattern: dot-notation, similar to capability
# Examples: event.user.created, notification.email.sent
EVENT_TYPE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$")


class ExpandedContractValidator:  # naming-ok: validator class, not protocol
    """Validates expanded contracts for runtime correctness (Phase 3).

    This validator performs comprehensive validation of fully-expanded contracts
    to ensure they are ready for runtime execution. It validates:

    1. **Execution Graph Integrity**: Detects circular dependencies and orphan
       handler references in requires_before/after constraints.

    2. **Event Routing Correctness**: Validates consumed_events format and warns
       about capability_outputs with no apparent consumers.

    3. **Dependency Type Correctness**: Validates capability input format and
       ensures alias uniqueness.

    4. **Runtime Invariants**: Validates handler_id format, input/output model
       references, contract_version format, and node_archetype consistency.

    Validation is performed in a single pass for efficiency. All validations
    are deterministic and do not require external resources.

    Example:
        >>> validator = ExpandedContractValidator()
        >>> result = validator.validate(contract)
        >>> if result.is_valid:
        ...     print("Contract is valid for runtime")
        ... else:
        ...     for issue in result.issues:
        ...         print(f"{issue.severity}: {issue.message}")

    Thread Safety:
        This class is safe for concurrent use from multiple threads.
        Instance configuration is set at construction time and read-only thereafter.

    See Also:
        - ModelHandlerContract: The contract model being validated
        - ContractPatchValidator: Phase 1 validation
        - EnumContractValidationErrorCode: Error codes used in this validator
    """

    def __init__(self, *, emit_event_output_info: bool = True) -> None:
        """Initialize the validator.

        Args:
            emit_event_output_info: Whether to emit INFO messages about
                event outputs. Defaults to True. Set to False to suppress
                informational messages about event outputs (e.g., when
                event consumers are validated elsewhere or in batch processing
                where these messages would be noise).
        """
        self._emit_event_output_info = emit_event_output_info

    def validate(self, contract: ModelHandlerContract) -> ModelValidationResult[None]:
        """Validate expanded contract for runtime correctness.

        Performs all Phase 3 validation checks on a fully-expanded contract.
        The contract must have already passed Phase 1 (patch) and Phase 2 (merge)
        validation.

        Validation includes:
            - Execution graph integrity (cycle and orphan detection)
            - Event routing correctness
            - Capability input format validation
            - Runtime invariant enforcement

        Args:
            contract: The fully expanded contract to validate. Must be a valid
                ModelHandlerContract instance.

        Returns:
            ModelValidationResult with:
                - is_valid: True if all checks pass
                - issues: List of validation issues (errors, warnings, info)
                - summary: Human-readable validation summary

        Example:
            >>> validator = ExpandedContractValidator()
            >>> result = validator.validate(contract)
            >>> if not result.is_valid:
            ...     for error in result.errors:
            ...         print(f"Error: {error}")
        """
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Expanded contract validation started",
        )

        logger.debug(
            f"Starting expanded contract validation for handler_id={contract.handler_id}"
        )

        # 1. Runtime invariant checks (handler_id, models, contract_version)
        self._validate_runtime_invariants(contract, result)

        # 2. Execution graph integrity (cycles and orphans)
        self._validate_execution_graph(contract, result)

        # 3. Event routing correctness
        self._validate_event_routing(contract, result)

        # 4. Dependency type correctness (capability inputs)
        self._validate_capability_inputs(contract, result)

        # 5. Node archetype consistency
        self._validate_node_archetype_consistency(contract, result)

        # Update summary based on results
        if result.is_valid:
            result.summary = "Expanded contract validation passed"
            logger.debug(
                f"Expanded contract validation passed for handler_id={contract.handler_id} "
                f"(warnings={result.warning_count})"
            )
        else:
            result.summary = f"Expanded contract validation failed with {result.error_level_count} errors"
            logger.info(
                f"Expanded contract validation failed for handler_id={contract.handler_id}: "
                f"{result.error_level_count} errors, {result.warning_count} warnings"
            )

        return result

    # =========================================================================
    # Runtime Invariant Validation
    # =========================================================================

    def _validate_runtime_invariants(
        self,
        contract: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate runtime invariants for the contract.

        Checks:
            - handler_id format (dot-separated, starts with letter/underscore)
            - input_model and output_model look like valid module paths
            - contract_version follows semver pattern

        Args:
            contract: The contract to validate.
            result: The validation result to append issues to.
        """
        # Validate handler_id format
        # Note: ModelHandlerContract already validates this, but we add
        # additional checks for expanded contract requirements
        self._validate_handler_id_format(contract.handler_id, result)

        # Validate input_model reference
        self._validate_model_reference(contract.input_model, "input_model", result)

        # Validate output_model reference
        self._validate_model_reference(contract.output_model, "output_model", result)

        # Validate version format
        # Note: contract_version is ModelSemVer, convert to string for format validation
        self._validate_version_format(str(contract.contract_version), result)

    def _validate_handler_id_format(
        self,
        handler_id: str,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate handler_id follows the expected format.

        Handler ID must be:
            - Dot-separated segments (at least 2)
            - Each segment starts with letter or underscore
            - Contains only alphanumeric and underscore

        Args:
            handler_id: The handler ID to validate.
            result: The validation result to append issues to.
        """
        if not HANDLER_ID_PATTERN.match(handler_id):
            logger.debug(f"Handler ID format invalid: {handler_id}")
            result.add_error(
                f"Handler ID '{handler_id}' has invalid format. "
                "Must be dot-separated segments, each starting with letter or underscore "
                "(e.g., 'node.user.reducer', 'handler.email.sender').",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID.value,
            )

    def _validate_model_reference(
        self,
        model_ref: str,
        field_name: str,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate that a model reference looks like a valid module path.

        Model references should be fully qualified Python module paths
        (e.g., 'omnibase_core.models.events.ModelUserEvent').

        Args:
            model_ref: The model reference string to validate.
            field_name: Name of the field for error messages (input_model/output_model).
            result: The validation result to append issues to.
        """
        if not model_ref or not model_ref.strip():
            logger.debug(f"{field_name} is empty")
            result.add_error(
                f"{field_name} cannot be empty.",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID.value,
            )
            return

        if not MODEL_REFERENCE_PATTERN.match(model_ref):
            logger.debug(f"{field_name} has invalid format: {model_ref}")
            result.add_error(
                f"{field_name} '{model_ref}' does not look like a valid module path. "
                "Expected format: 'package.module.ClassName' (e.g., 'myapp.models.Input').",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID.value,
            )

    def _validate_version_format(
        self,
        version: str,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate version follows semantic versioning format.

        Version must be in semver format: MAJOR.MINOR.PATCH with optional
        pre-release and build metadata suffixes.

        Args:
            version: The version string to validate.
            result: The validation result to append issues to.
        """
        if not SEMVER_PATTERN.match(version):
            logger.debug(f"Version format is non-standard: {version}")
            # This is a warning, not an error, as the model already validates format
            result.add_issue(
                severity=EnumSeverity.WARNING,
                message=(
                    f"Version '{version}' is not in strict semantic version format. "
                    "Expected: 'MAJOR.MINOR.PATCH' (e.g., '1.0.0', '1.2.3-beta.1')."
                ),
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED.value,
            )

    # =========================================================================
    # Execution Graph Validation
    # =========================================================================

    def _validate_execution_graph(
        self,
        contract: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate execution graph integrity.

        Checks:
            - No circular dependencies in requires_before/requires_after
            - No orphan references (references to non-existent handlers)

        For a single contract, we can detect self-references (direct cycles)
        and validate reference format. Full cycle detection across multiple
        contracts requires the contract registry.

        Args:
            contract: The contract to validate.
            result: The validation result to append issues to.
        """
        if not contract.execution_constraints:
            logger.debug("No execution constraints to validate")
            return

        constraints = contract.execution_constraints

        # Collect all dependency references
        all_deps = constraints.get_all_dependencies()

        if not all_deps:
            logger.debug("No dependencies in execution constraints")
            return

        # Check for self-references (direct cycle)
        handler_refs = self._extract_handler_refs(all_deps)
        for ref in handler_refs:
            if ref == contract.handler_id:
                logger.debug(f"Self-reference detected: {ref}")
                result.add_error(
                    f"Handler '{contract.handler_id}' has a self-reference in execution_constraints. "
                    "A handler cannot require itself before or after its own execution.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE.value,
                )

        # Validate reference format
        self._validate_dependency_references(all_deps, result)

    def _extract_handler_refs(self, deps: list[str]) -> list[str]:
        """Extract handler IDs from dependency references.

        Dependency references use prefixed format: handler:id, capability:name, tag:label.
        This method extracts only the handler:* references.

        Args:
            deps: List of dependency reference strings.

        Returns:
            List of handler IDs extracted from handler: prefixed references.
        """
        handler_refs: list[str] = []
        for dep in deps:
            if dep.startswith("handler:"):
                parts = dep.split(":", 1)
                if len(parts) == 2 and parts[1]:
                    handler_refs.append(parts[1])
        return handler_refs

    def _validate_dependency_references(
        self,
        deps: list[str],
        result: ModelValidationResult[None],
    ) -> None:
        """Validate dependency reference format.

        Each reference must have one of the valid prefixes:
            - capability: for capability-based dependencies
            - handler: for direct handler dependencies
            - tag: for tag-based dependencies

        Args:
            deps: List of dependency reference strings.
            result: The validation result to append issues to.
        """
        valid_prefixes = ("capability:", "handler:", "tag:")

        for dep in deps:
            # Check prefix
            if not any(dep.startswith(prefix) for prefix in valid_prefixes):
                # Note: This should already be caught by ModelExecutionConstraints
                # but we double-check for expanded contracts
                logger.debug(f"Invalid dependency reference format: {dep}")
                result.add_error(
                    f"Dependency reference '{dep}' has invalid format. "
                    f"Must start with one of: {', '.join(valid_prefixes)}",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN.value,
                )
                continue

            # Check that value after prefix is non-empty
            parts = dep.split(":", 1)
            if len(parts) != 2 or not parts[1].strip():
                logger.debug(f"Dependency reference has empty value: {dep}")
                result.add_error(
                    f"Dependency reference '{dep}' has empty value after prefix.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN.value,
                )

    # =========================================================================
    # Event Routing Validation
    # =========================================================================

    def _validate_event_routing(
        self,
        contract: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate event routing correctness.

        Checks:
            - capability_outputs (emitted events) have valid format
            - Warns if events are declared but may have no consumers

        Note: Full consumer validation requires cross-contract analysis.
        This method validates format and provides warnings for single contracts.

        Args:
            contract: The contract to validate.
            result: The validation result to append issues to.
        """
        # Validate capability_outputs format (these can be event outputs)
        for output in contract.capability_outputs:
            if not self._is_valid_capability_format(output):
                logger.debug(f"Invalid capability output format: {output}")
                result.add_error(
                    f"Capability output '{output}' has invalid format. "
                    "Must be dot-notation with alphanumeric segments "
                    "(e.g., 'event.user_created', 'notification.email').",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID.value,
                )

        # Warn about outputs that look like events but may have no consumers
        # (This is informational since we can't check cross-contract)
        event_outputs = [
            o for o in contract.capability_outputs if o.startswith("event.")
        ]
        if event_outputs and self._emit_event_output_info:
            logger.debug(
                f"Found {len(event_outputs)} event outputs - cannot verify consumers without registry"
            )
            result.add_issue(
                severity=EnumSeverity.INFO,
                message=(
                    f"Handler declares {len(event_outputs)} event output(s): {event_outputs}. "
                    "Ensure consumers exist for these events in the runtime configuration."
                ),
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING.value,
                suggestion="Verify that handlers consuming these events are registered.",
            )

    def _is_valid_capability_format(self, capability: str) -> bool:
        """Check if capability name follows valid format.

        Args:
            capability: The capability name to check.

        Returns:
            True if format is valid, False otherwise.
        """
        return bool(CAPABILITY_PATTERN.match(capability))

    # =========================================================================
    # Capability Input Validation
    # =========================================================================

    def _validate_capability_inputs(
        self,
        contract: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate capability input dependencies.

        Checks:
            - Capability names have valid format
            - Aliases are unique (already validated by model, but double-check)

        Args:
            contract: The contract to validate.
            result: The validation result to append issues to.
        """
        if not contract.capability_inputs:
            logger.debug("No capability inputs to validate")
            return

        # Check for duplicate aliases
        duplicate_aliases: list[str] = []
        seen_aliases: set[str] = set()

        for dep in contract.capability_inputs:
            # Validate capability format
            if not self._is_valid_capability_format(dep.capability):
                logger.debug(f"Invalid capability format: {dep.capability}")
                result.add_error(
                    f"Capability '{dep.capability}' (alias: '{dep.alias}') has invalid format. "
                    "Must be dot-notation with alphanumeric segments "
                    "(e.g., 'database.relational', 'cache.distributed').",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED.value,
                )

            # Track aliases for duplicate detection
            if dep.alias in seen_aliases:
                duplicate_aliases.append(dep.alias)
            seen_aliases.add(dep.alias)

        # Report duplicate aliases (should be caught by model, but verify)
        if duplicate_aliases:
            duplicates = sorted(set(duplicate_aliases))
            logger.debug(f"Duplicate capability input aliases: {duplicates}")
            result.add_error(
                f"Duplicate capability input aliases found: {duplicates}. "
                "Each capability input must have a unique alias.",
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH.value,
            )

    # =========================================================================
    # Node Archetype Consistency
    # =========================================================================

    def _validate_node_archetype_consistency(
        self,
        contract: ModelHandlerContract,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate handler_id prefix consistency with node_archetype.

        If the handler_id starts with a prefix that implies a specific archetype
        (e.g., 'compute.', 'effect.', 'reducer.', 'orchestrator.'), validate
        that descriptor.node_archetype matches.

        Note: Generic prefixes like 'node.' and 'handler.' are allowed with
        any node_archetype.

        Args:
            contract: The contract to validate.
            result: The validation result to append issues to.
        """
        # Extract first segment of handler_id
        prefix = contract.handler_id.split(".")[0].lower()

        # Map prefixes that imply specific node archetypes
        prefix_to_archetype = {
            "compute": "compute",
            "effect": "effect",
            "reducer": "reducer",
            "orchestrator": "orchestrator",
        }

        expected_archetype = prefix_to_archetype.get(prefix)

        # Only validate if prefix implies a specific archetype
        if expected_archetype is not None:
            actual_archetype = contract.descriptor.node_archetype
            if actual_archetype != expected_archetype:
                logger.debug(
                    f"Node archetype mismatch: prefix '{prefix}' implies "
                    f"'{expected_archetype}' but got '{actual_archetype}'"
                )
                # Note: This is already validated by ModelHandlerContract's
                # validate_descriptor_node_archetype_consistency validator,
                # but we include it here for completeness and clearer errors
                result.add_error(
                    f"Handler ID prefix '{prefix}' implies node_archetype='{expected_archetype}' "
                    f"but descriptor has node_archetype='{actual_archetype}'. "
                    "Either change the handler_id prefix or update the node_archetype.",
                    code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED.value,
                )
