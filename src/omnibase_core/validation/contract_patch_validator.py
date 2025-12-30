# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Patch Validator.

Validates contract patches before merge into base contracts.
Part of the contract patching system for OMN-1126.

Validation Philosophy:
    - Structural: Validates shape and syntax
    - Semantic: Validates internal consistency
    - NOT Resolutive: Does not resolve profiles or models

Related:
    - OMN-1126: ModelContractPatch & Patch Validation

.. versionadded:: 0.4.0
"""

from pathlib import Path

from pydantic import ValidationError

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = [
    "ContractPatchValidator",
]


class ContractPatchValidator:
    """Validates contract patches before merge.

    This validator performs structural and semantic validation of contract
    patches without requiring runtime resolution of profiles or models.
    Validation is deterministic and environment-agnostic.

    Validation Checks:
        - Structural: Pydantic model validation (extra="forbid")
        - Identity: New contracts must have name + version
        - List Operations: Valid __add/__remove syntax
        - Descriptor: Nested descriptor patch validation

    Non-Validation (Deferred):
        - Profile existence (deferred to factory)
        - Model resolution (deferred to expansion)
        - Capability compatibility (deferred to merge)

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
        """Validate a contract patch.

        Performs all validation checks on an already-parsed patch.
        Since the patch is already a ModelContractPatch, Pydantic validation
        has already passed; this method adds semantic validation.

        Args:
            patch: The contract patch to validate.

        Returns:
            Validation result with is_valid flag and any issues found.
        """
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Patch validation started",
        )

        # Check for conflicting list operations
        self._validate_list_operation_conflicts(patch, result)

        # Check descriptor patch if present
        if patch.descriptor is not None:
            self._validate_descriptor_patch(patch, result)

        # Check identity field consistency (already done by Pydantic, but add context)
        self._validate_identity_fields(patch, result)

        # Check profile reference format
        self._validate_profile_reference(patch, result)

        # Update summary based on results
        if result.is_valid:
            result.summary = "Patch validation passed"
        else:
            result.summary = f"Patch validation failed with {result.error_count} errors"

        return result

    def validate_dict(
        self, data: dict[str, object]
    ) -> ModelValidationResult[ModelContractPatch]:
        """Validate a dictionary as a contract patch.

        Parses the dictionary into a ModelContractPatch and validates it.
        This is useful for validating user-provided data before processing.

        Args:
            data: Dictionary representation of a contract patch.

        Returns:
            Validation result with parsed patch if valid.
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
            result.is_valid = False
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                result.add_error(
                    f"Validation error at '{field_path}': {error['msg']}",
                    code="PYDANTIC_VALIDATION_ERROR",
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

        Args:
            path: Path to the YAML file.

        Returns:
            Validation result with parsed patch if valid.
        """
        result: ModelValidationResult[ModelContractPatch] = ModelValidationResult(
            is_valid=True,
            summary="File validation started",
        )

        # Check file exists
        if not path.exists():
            result.is_valid = False
            result.add_error(
                f"File not found: {path}",
                code="FILE_NOT_FOUND",
                file_path=path,
            )
            result.summary = "File validation failed: file not found"
            return result

        # Check file extension
        if path.suffix.lower() not in (".yaml", ".yml"):
            result.add_warning(
                f"Expected .yaml or .yml extension, got: {path.suffix}",
                code="UNEXPECTED_EXTENSION",
                file_path=path,
            )

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            result.is_valid = False
            result.add_error(
                f"File read error: {e}",
                code="FILE_READ_ERROR",
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
            result.is_valid = False
            result.add_error(
                f"YAML parsing or validation error: {e.message}",
                code="YAML_VALIDATION_ERROR",
                file_path=path,
            )
            result.summary = "File validation failed: YAML validation error"

        except ValidationError as e:
            result.is_valid = False
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                result.add_error(
                    f"Validation error at '{field_path}': {error['msg']}",
                    code="PYDANTIC_VALIDATION_ERROR",
                )
            result.summary = f"File validation failed with {len(e.errors())} errors"

        return result

    # =========================================================================
    # Private Validation Methods
    # =========================================================================

    def _validate_list_operation_conflicts(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Check for conflicting list operations.

        Validates that no item appears in both __add and __remove lists
        for the same field, which would be semantically contradictory.
        Also checks for duplicate entries within add lists.

        Validates the following fields:
            - handlers__add / handlers__remove
            - dependencies__add / dependencies__remove
            - consumed_events__add / consumed_events__remove
            - capability_inputs__add / capability_inputs__remove
            - capability_outputs__add / capability_outputs__remove

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.
        """
        # Check handlers
        if patch.handlers__add and patch.handlers__remove:
            add_names = {h.name for h in patch.handlers__add}
            remove_names = set(patch.handlers__remove)
            conflicts = add_names & remove_names
            if conflicts:
                result.add_error(
                    f"Handler(s) appear in both add and remove: {conflicts}",
                    code="CONFLICTING_LIST_OPERATIONS",
                )

        # Check dependencies
        if patch.dependencies__add and patch.dependencies__remove:
            add_names = {d.name for d in patch.dependencies__add}
            remove_names = set(patch.dependencies__remove)
            conflicts = add_names & remove_names
            if conflicts:
                result.add_error(
                    f"Dependency(s) appear in both add and remove: {conflicts}",
                    code="CONFLICTING_LIST_OPERATIONS",
                )

        # Check events
        if patch.consumed_events__add and patch.consumed_events__remove:
            add_events = set(patch.consumed_events__add)
            remove_events = set(patch.consumed_events__remove)
            conflicts = add_events & remove_events
            if conflicts:
                result.add_error(
                    f"Event(s) appear in both add and remove: {conflicts}",
                    code="CONFLICTING_LIST_OPERATIONS",
                )

        # Check for duplicate capability outputs within __add
        if patch.capability_outputs__add:
            cap_names = [cap.name for cap in patch.capability_outputs__add]
            seen: set[str] = set()
            duplicates: set[str] = set()
            for name in cap_names:
                if name in seen:
                    duplicates.add(name)
                seen.add(name)
            if duplicates:
                result.add_error(
                    f"Duplicate capability output(s) in add list: {duplicates}",
                    code="DUPLICATE_LIST_ENTRIES",
                )

        # Check capability inputs for add/remove conflicts
        if patch.capability_inputs__add and patch.capability_inputs__remove:
            add_inputs = set(patch.capability_inputs__add)
            remove_inputs = set(patch.capability_inputs__remove)
            conflicts = add_inputs & remove_inputs
            if conflicts:
                result.add_error(
                    f"Capability input(s) appear in both add and remove: {conflicts}",
                    code="CONFLICTING_LIST_OPERATIONS",
                )

        # Check capability outputs for add/remove conflicts
        if patch.capability_outputs__add and patch.capability_outputs__remove:
            add_output_names = {cap.name for cap in patch.capability_outputs__add}
            remove_output_names = set(patch.capability_outputs__remove)
            conflicts = add_output_names & remove_output_names
            if conflicts:
                result.add_error(
                    f"Capability output(s) appear in both add and remove: {conflicts}",
                    code="CONFLICTING_LIST_OPERATIONS",
                )

        # Check for duplicate capability inputs within __add
        if patch.capability_inputs__add:
            seen_inputs: set[str] = set()
            duplicate_inputs: set[str] = set()
            for name in patch.capability_inputs__add:
                if name in seen_inputs:
                    duplicate_inputs.add(name)
                seen_inputs.add(name)
            if duplicate_inputs:
                result.add_error(
                    f"Duplicate capability input(s) in add list: {duplicate_inputs}",
                    code="DUPLICATE_LIST_ENTRIES",
                )

    def _validate_descriptor_patch(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate the nested descriptor patch.

        Checks the descriptor patch for semantic consistency:
            - Warns if descriptor patch is present but empty (no overrides)
            - Warns if purity='pure' conflicts with idempotent=False

        Args:
            patch: The contract patch containing the descriptor to validate.
            result: The validation result to append issues to.
        """
        if patch.descriptor is None:
            return

        # Check for empty descriptor patch (warning, not error)
        if not patch.descriptor.has_overrides():
            result.add_issue(
                severity=EnumValidationSeverity.WARNING,
                message="Descriptor patch is present but has no overrides",
                code="EMPTY_DESCRIPTOR_PATCH",
                suggestion="Remove the empty descriptor field or add overrides",
            )

        # Check purity/idempotent consistency
        if patch.descriptor.purity == "pure" and patch.descriptor.idempotent is False:
            result.add_issue(
                severity=EnumValidationSeverity.WARNING,
                message=(
                    "Descriptor declares purity='pure' but idempotent=False. "
                    "Pure functions are typically idempotent."
                ),
                code="PURITY_IDEMPOTENT_MISMATCH",
                suggestion="Consider setting idempotent=True for pure handlers",
            )

    def _validate_identity_fields(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate identity field consistency.

        Checks that identity fields (name, node_version) are consistent.
        Pydantic already validates that both must be present or both absent;
        this method adds informational context about the patch type.

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.
        """
        # This is already validated by Pydantic, but add informational context
        if patch.is_new_contract:
            result.add_issue(
                severity=EnumValidationSeverity.INFO,
                message=f"Patch declares new contract identity: {patch.name}",
                code="NEW_CONTRACT_IDENTITY",
            )

    def _validate_profile_reference(
        self,
        patch: ModelContractPatch,
        result: ModelValidationResult[None],
    ) -> None:
        """Validate profile reference format (structural only).

        Performs structural validation of the profile reference without
        attempting to resolve the profile. Checks:
            - Profile name follows lowercase_with_underscores convention
            - Version string contains digits (basic semver format check)

        Note:
            Profile existence is NOT validated here; that is deferred to
            the factory at contract expansion time.

        Args:
            patch: The contract patch to validate.
            result: The validation result to append issues to.
        """
        profile = patch.extends.profile
        version = patch.extends.version

        # Check profile name format (lowercase with underscores)
        if not all(c.isalnum() or c == "_" for c in profile):
            result.add_warning(
                f"Profile name '{profile}' contains non-standard characters. "
                "Recommended format: lowercase_with_underscores",
                code="NON_STANDARD_PROFILE_NAME",
            )
        elif any(c.isupper() for c in profile):
            result.add_warning(
                f"Profile name '{profile}' contains uppercase characters. "
                "Recommended format: lowercase_with_underscores",
                code="NON_STANDARD_PROFILE_NAME",
            )

        # Check version format (basic semver check)
        if version and not any(c.isdigit() for c in version):
            result.add_warning(
                f"Version '{version}' does not contain digits. "
                "Expected semantic version format (e.g., '1.0.0').",
                code="NON_STANDARD_VERSION_FORMAT",
            )
