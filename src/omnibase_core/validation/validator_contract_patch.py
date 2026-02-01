"""
Contract Patch Validator.

Validates contract patches before merge into base contracts.
Part of the contract patching system for OMN-1126.

Validation Philosophy:
    - Structural: Validates shape and syntax
    - Semantic: Validates internal consistency
    - NOT Resolutive: Does not resolve profiles or models

Logging Conventions:
    - DEBUG: Detailed trace information (validation steps, field checks)
    - INFO: High-level operation summaries (validation started/passed/failed)
    - WARNING: Recoverable issues that don't fail validation
    - ERROR: Failures that will fail validation

Error Code Conventions:
    Error codes in this module use the CONTRACT_PATCH_* prefix for consistent
    categorization per PR #289. All codes are defined in EnumPatchValidationErrorCode:
    - CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES: Duplicate items within an add list
    - CONTRACT_PATCH_EMPTY_DESCRIPTOR: Behavior patch with no overrides
    - CONTRACT_PATCH_PURITY_IDEMPOTENT_MISMATCH: Conflicting purity/idempotent settings
    - CONTRACT_PATCH_NEW_IDENTITY: Informational - new contract identity declared
    - CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME: Profile name doesn't follow conventions
    - CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT: Version format is non-standard
    - CONTRACT_PATCH_FILE_NOT_FOUND: File does not exist
    - CONTRACT_PATCH_FILE_READ_ERROR: File could not be read
    - CONTRACT_PATCH_UNEXPECTED_EXTENSION: File has unexpected extension
    - CONTRACT_PATCH_YAML_VALIDATION_ERROR: YAML parsing or validation error
    - CONTRACT_PATCH_PYDANTIC_VALIDATION_ERROR: Pydantic model validation error

Related:
    - OMN-1126: ModelContractPatch & Patch Validation

.. versionadded:: 0.4.0
"""

import logging
import re
from pathlib import Path

from pydantic import ValidationError

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_patch_validation_error_code import (
    EnumPatchValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = [
    "ContractPatchValidator",
]

# Configure logger for this module
logger = logging.getLogger(__name__)

# Semver pattern for version validation
# Matches: 1.0.0, ^1.0.0, ~1.0, >=1.0.0, <2.0.0, etc.
# Optional prefix: ^, ~, >=, >, <=, <, =
# Core version: major.minor with optional .patch
# Optional suffix: -alpha, -beta.1, +build.123, etc.
SEMVER_PATTERN = re.compile(r"^[~^>=<]*\d+\.\d+(\.\d+)?([-.+][\w.]+)?$")


class ContractPatchValidator:
    """Validates contract patches before merge.

    This validator performs structural and semantic validation of contract
    patches without requiring runtime resolution of profiles or models.
    Validation is deterministic and environment-agnostic.

    Validation Checks:
        - Structural: Pydantic model validation (extra="forbid")
        - Identity: New contracts must have name + version
        - List Operations: Duplicate detection within add lists
        - Behavior: Nested behavior patch validation (via descriptor field)

    Non-Validation (Deferred):
        - Profile existence (deferred to factory)
        - Model resolution (deferred to expansion)
        - Capability compatibility (deferred to merge)

    Note:
        Conflict checks (items in both __add and __remove) are handled by
        Pydantic model validation in ModelContractPatch.validate_no_add_remove_conflicts().
        This validator focuses on duplicate detection within lists.

    Example:
        >>> validator = ContractPatchValidator()
        >>> result = validator.validate(patch)
        >>> if result.is_valid:
        ...     print("Patch is valid")
        ... else:
        ...     for issue in result.issues:
        ...         print(f"{issue.severity}: {issue.message}")

    See Also:
        - ModelContractPatch: The model being validated
        - ProtocolPatchValidator: Protocol this implements
    """

    def validate(self, patch: ModelContractPatch) -> ModelValidationResult[None]:
        """Validate a contract patch for semantic correctness.

        Performs all validation checks on an already-parsed patch.
        Since the patch is already a ModelContractPatch, Pydantic validation
        has already passed; this method adds semantic validation.

        Validation includes:
            - Duplicate detection within add lists
            - Behavior patch consistency (timeout vs retry, purity vs idempotent)
            - Identity field verification (name + version pairing)
            - Profile reference format checking

        Note:
            Conflict checks (add vs remove) are already handled by Pydantic
            model validation and are not duplicated here.

        Args:
            patch: The contract patch to validate. Must be a valid
                ModelContractPatch instance (Pydantic validation passed).

        Returns:
            ModelValidationResult with:
                - is_valid: True if all checks pass
                - issues: List of validation issues (errors, warnings, info)
                - summary: Human-readable validation summary

        Example:
            >>> validator = ContractPatchValidator()
            >>> result = validator.validate(patch)
            >>> if not result.is_valid:
            ...     for error in result.errors:
            ...         print(f"Error: {error}")
        """
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Patch validation started",
        )

        logger.debug(
            f"Starting patch validation for profile={patch.extends.profile}, "
            f"is_new_contract={patch.is_new_contract}"
        )

        # Check for duplicate entries within add lists
        # Note: Conflict checks (add vs remove) are handled by Pydantic model validation
        self._validate_list_operation_duplicates(patch, result)

        # Check behavior patch (descriptor field) if present
        if patch.descriptor is not None:
            self._validate_behavior_patch(patch, result)

        # Check identity field consistency (already done by Pydantic, but add context)
        self._validate_identity_fields(patch, result)

        # Check profile reference format
        self._validate_profile_reference(patch, result)

        # Update summary based on results
        if result.is_valid:
            result.summary = "Patch validation passed"
            logger.debug(
                f"Patch validation passed for profile={patch.extends.profile} "
                f"(warnings={result.warning_count})"
            )
        else:
            result.summary = (
                f"Patch validation failed with {result.error_level_count} errors"
            )
            logger.info(
                f"Patch validation failed for profile={patch.extends.profile}: "
                f"{result.error_level_count} errors, {result.warning_count} warnings"
            )

        return result

    def validate_dict(
        self, data: dict[str, object]
    ) -> ModelValidationResult[ModelContractPatch]:
        """Validate a dictionary as a contract patch.

        Parses the dictionary into a ModelContractPatch and validates it.
        This is useful for validating user-provided data (e.g., from API
        requests or configuration files) before processing.

        Performs both Pydantic structural validation and semantic validation.
        If Pydantic validation fails, the result contains detailed error
        messages including field paths.

        Args:
            data: Dictionary representation of a contract patch. Must contain
                at least an 'extends' field with profile reference.

        Returns:
            ModelValidationResult with:
                - is_valid: True if both parsing and validation pass
                - validated_value: Parsed ModelContractPatch if valid
                - errors: List of validation errors if invalid
                - summary: Human-readable validation summary

        Example:
            >>> validator = ContractPatchValidator()
            >>> data = {
            ...     "extends": {"profile": "compute_pure", "version": "1.0.0"},
            ...     "description": "My patch"
            ... }
            >>> result = validator.validate_dict(data)
            >>> if result.is_valid:
            ...     patch = result.validated_value
        """
        result: ModelValidationResult[ModelContractPatch] = ModelValidationResult(
            is_valid=True,
            summary="Dictionary validation started",
        )

        try:
            patch = ModelContractPatch.model_validate(data)
            result.validated_value = patch

            # Run semantic validation
            semantic_result = self.validate(patch)
            if not semantic_result.is_valid:
                result.is_valid = False
                result.issues.extend(semantic_result.issues)
                result.errors.extend(semantic_result.errors)
                result.warnings.extend(semantic_result.warnings)
                result.summary = semantic_result.summary
            else:
                result.summary = "Dictionary validation passed"

        except ValidationError as e:
            logger.debug(f"Dictionary validation failed: {len(e.errors())} errors")
            result.is_valid = False
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                result.add_error(
                    f"Validation error at '{field_path}': {error['msg']}",
                    code=EnumPatchValidationErrorCode.CONTRACT_PATCH_PYDANTIC_VALIDATION_ERROR.value,
                )
            result.summary = (
                f"Dictionary validation failed with {len(e.errors())} errors"
            )

        return result

    def validate_file(self, path: Path) -> ModelValidationResult[ModelContractPatch]:
        """Validate a YAML file as a contract patch.

        Reads and parses the YAML file, then validates as a contract patch.
        Uses Pydantic model validation for type-safe YAML loading.
        Handles file I/O errors and YAML parsing errors gracefully.

        Validation stages:
            1. File existence check
            2. File extension check (warning for non-.yaml/.yml)
            3. File read (with encoding handling)
            4. YAML parsing
            5. Pydantic model validation
            6. Semantic validation

        Args:
            path: Path to the YAML file. Should have .yaml or .yml extension.

        Returns:
            ModelValidationResult with:
                - is_valid: True if file is valid contract patch
                - validated_value: Parsed ModelContractPatch if valid
                - errors: List of validation errors if invalid
                - warnings: Non-fatal issues (e.g., unexpected extension)
                - summary: Human-readable validation summary

        Example:
            >>> from pathlib import Path
            >>> validator = ContractPatchValidator()
            >>> result = validator.validate_file(Path("my_patch.yaml"))
            >>> if result.is_valid:
            ...     patch = result.validated_value
            ...     print(f"Validated: {patch.extends.profile}")
        """
        result: ModelValidationResult[ModelContractPatch] = ModelValidationResult(
            is_valid=True,
            summary="File validation started",
        )

        # Check file exists
        if not path.exists():
            logger.error(f"File not found: {path}")
            result.is_valid = False
            result.add_error(
                f"File not found: {path}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_FILE_NOT_FOUND.value,
                file_path=path,
            )
            result.summary = "File validation failed: file not found"
            return result

        # Check file extension
        if path.suffix.lower() not in (".yaml", ".yml"):
            logger.warning(f"Unexpected file extension for {path}: {path.suffix}")
            result.add_warning(
                f"Expected .yaml or .yml extension, got: {path.suffix}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_UNEXPECTED_EXTENSION.value,
                file_path=path,
            )

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"File read error for {path}: {e}")
            result.is_valid = False
            result.add_error(
                f"File read error: {e}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_FILE_READ_ERROR.value,
                file_path=path,
            )
            result.summary = "File validation failed: file read error"
            return result

        # Parse YAML and validate with Pydantic model
        try:
            patch = load_yaml_content_as_model(content, ModelContractPatch)
            result.validated_value = patch

            # Run semantic validation
            semantic_result = self.validate(patch)
            if not semantic_result.is_valid:
                result.is_valid = False
                result.issues.extend(semantic_result.issues)
                result.errors.extend(semantic_result.errors)
                result.warnings.extend(semantic_result.warnings)
                result.summary = semantic_result.summary.replace("Patch", "File")
            else:
                result.summary = "File validation passed"

        except ModelOnexError as e:
            logger.warning(f"YAML parsing or validation error for {path}: {e.message}")
            result.is_valid = False
            result.add_error(
                f"YAML parsing or validation error: {e.message}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_YAML_VALIDATION_ERROR.value,
                file_path=path,
            )
            result.summary = "File validation failed: YAML validation error"

        # Note: ValidationError is not caught here because load_yaml_content_as_model
        # wraps ValidationError in ModelOnexError (see util_safe_yaml_loader.py).
        # The ModelOnexError handler above handles all validation-related errors.

        return result

    # =========================================================================
    # Private Validation Methods
    # =========================================================================

    def _find_duplicates_in_list(self, names: list[str]) -> set[str]:
        """Find duplicate entries in a list of names.

        Iterates through the list tracking seen items and returns
        any names that appear more than once.

        Args:
            names: List of string names to check for duplicates.

        Returns:
            Set of names that appear more than once. Empty set if no duplicates.

        Complexity:
            Time: O(n) - single pass through the list with O(1) set operations.
            Space: O(n) - stores up to n items in the `seen` set.
        """
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        return duplicates

    def _check_duplicates_in_list(
        self,
        names: list[str],
        field_name: str,
        result: ModelValidationResult[None],
    ) -> None:
        """Check for duplicate entries in a list and add errors if found.

        Uses _find_duplicates_in_list to detect duplicates and adds an error
        to the validation result with the DUPLICATE_LIST_ENTRIES code.

        Note:
            Duplicates are sorted alphabetically in error messages to ensure
            deterministic output regardless of insertion order.

        Args:
            names: List of string names to check for duplicates.
            field_name: Human-readable field name for error messages
                (e.g., "handler", "dependency", "capability output").
            result: The validation result to append issues to.
        """
        duplicates = self._find_duplicates_in_list(names)
        if duplicates:
            # Sort duplicates for deterministic error messages
            sorted_duplicates = sorted(duplicates)
            logger.debug(
                f"Found duplicate {field_name}s in add list: {sorted_duplicates}"
            )
            result.add_error(
                f"Duplicate {field_name}(s) in add list: {sorted_duplicates}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES.value,
            )

    def _validate_list_operation_duplicates(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Check for duplicate entries within add lists.

        Validates that no duplicate entries exist within __add lists,
        which would be semantically redundant and could indicate errors.

        Note:
            Conflict checks (items in both __add and __remove) are handled
            by Pydantic model validation via validate_no_add_remove_conflicts.
            This method only checks for duplicates within individual lists.

        Validates the following add lists:
            - handlers__add (duplicate handler names)
            - dependencies__add (duplicate dependency names)
            - capability_outputs__add (duplicate capability names)
            - capability_inputs__add (duplicate input names)
            - consumed_events__add (duplicate event type names)

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.
        """
        # Check for duplicate handlers within __add
        if patch.handlers__add:
            handler_names = [h.name for h in patch.handlers__add]
            self._check_duplicates_in_list(handler_names, "handler", result)

        # Check for duplicate dependencies within __add
        if patch.dependencies__add:
            dep_names = [d.name for d in patch.dependencies__add]
            self._check_duplicates_in_list(dep_names, "dependency", result)

        # Check for duplicate capability outputs within __add
        if patch.capability_outputs__add:
            cap_names = [cap.name for cap in patch.capability_outputs__add]
            self._check_duplicates_in_list(cap_names, "capability output", result)

        # Check for duplicate capability inputs within __add
        if patch.capability_inputs__add:
            self._check_duplicates_in_list(
                list(patch.capability_inputs__add), "capability input", result
            )

        # Check for duplicate consumed events within __add
        if patch.consumed_events__add:
            self._check_duplicates_in_list(
                list(patch.consumed_events__add), "consumed event", result
            )

    def _validate_behavior_patch(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate the nested behavior patch in the descriptor field.

        Checks the behavior patch (stored in the `descriptor` field) for
        semantic consistency. The behavior patch contains handler behavior
        overrides such as timeout, retry, and concurrency settings.

        Validates:
            - Warns if behavior patch is present but empty (no overrides)
            - Warns if purity='pure' conflicts with idempotent=False

        Args:
            patch: The contract patch containing the behavior patch to validate.
            result: The validation result to append issues to.

        Note:
            The field is named 'descriptor' for historical reasons but
            conceptually represents handler behavior configuration
            (timeout, retry, concurrency).

            Empty behavior patches generate an INFO (not WARNING/ERROR) because:
            1. An empty behavior patch is semantically valid (just a no-op)
            2. It's likely a user mistake but doesn't break merge operations
            3. The patch system should be permissive for forward compatibility
            Users are encouraged to remove empty behavior patches for clarity.
        """
        if patch.descriptor is None:
            return

        # Check for empty behavior patch (info, not warning/error - see docstring rationale)
        if not patch.descriptor.has_overrides():
            logger.debug("Behavior patch has no overrides - issuing info")
            result.add_issue(
                severity=EnumSeverity.INFO,
                message="Behavior patch is present but has no overrides",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_EMPTY_DESCRIPTOR.value,
                suggestion="Remove the empty descriptor field or add behavior overrides",
            )

        # Check purity/idempotent consistency
        if patch.descriptor.purity == "pure" and patch.descriptor.idempotent is False:
            logger.debug(
                "Behavior patch has purity/idempotent mismatch - issuing warning"
            )
            result.add_issue(
                severity=EnumSeverity.WARNING,
                message=(
                    "Behavior declares purity='pure' but idempotent=False. "
                    "Pure functions are typically idempotent."
                ),
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_PURITY_IDEMPOTENT_MISMATCH.value,
                suggestion="Consider setting idempotent=True for pure handlers",
            )

    def _validate_identity_fields(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate identity field consistency and add context.

        Checks that identity fields (name, node_version) are consistent.
        Pydantic already validates that both must be present or both absent;
        this method adds informational context about the patch type.

        For new contracts (those with identity fields), an INFO-level issue
        is added to document the contract name being declared.

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.

        Note:
            Identity validation is also performed by Pydantic in
            ModelContractPatch.validate_identity_consistency(). This method
            provides additional context rather than duplicate validation.
        """
        # This is already validated by Pydantic, but add informational context
        if patch.is_new_contract:
            result.add_issue(
                severity=EnumSeverity.INFO,
                message=f"Patch declares new contract identity: {patch.name}",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_NEW_IDENTITY.value,
            )

    def _validate_profile_reference(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate profile reference format (structural only).

        Performs structural validation of the profile reference without
        attempting to resolve the profile. This is intentional: profile
        resolution is deferred to the factory at contract expansion time.

        Validates:
            - Profile name follows lowercase_with_underscores convention
            - Profile name contains only alphanumeric characters and underscores
            - Version string contains at least one digit (basic semver check)

        Non-standard names or versions generate warnings (not errors) to allow
        flexibility while encouraging best practices.

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.

        Note:
            Profile existence is NOT validated here; that is deferred to
            the factory at contract expansion time. This ensures validation
            is environment-agnostic and can run without profile registry access.

        Example:
            Valid profiles: 'compute_pure', 'effect_http_v2'
            Non-standard: 'ComputePure' (uppercase), 'my-profile' (hyphens)
        """
        profile = patch.extends.profile
        version = patch.extends.version

        # Check profile name format (lowercase with underscores)
        if not all(c.isalnum() or c == "_" for c in profile):
            result.add_warning(
                f"Profile name '{profile}' contains non-standard characters. "
                "Recommended format: lowercase_with_underscores",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME.value,
            )
        elif any(c.isupper() for c in profile):
            result.add_warning(
                f"Profile name '{profile}' contains uppercase characters. "
                "Recommended format: lowercase_with_underscores",
                code=EnumPatchValidationErrorCode.CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME.value,
            )

        # Check version format (semver validation)
        if version:
            if not any(c.isdigit() for c in version):
                # No digits at all - definitely not a version
                result.add_warning(
                    f"Version '{version}' does not contain digits. "
                    "Expected semantic version format (e.g., '1.0.0').",
                    code=EnumPatchValidationErrorCode.CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT.value,
                )
            elif not SEMVER_PATTERN.match(version):
                # Has digits but not in standard semver format
                result.add_warning(
                    f"Version '{version}' is not in standard semantic version format. "
                    "Expected formats: '1.0.0', '^1.0.0', '~1.0', '>=1.0.0'.",
                    code=EnumPatchValidationErrorCode.CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT.value,
                )
