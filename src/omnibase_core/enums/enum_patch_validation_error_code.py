# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Patch validation error codes for contract patch validation.

These error codes are used by ContractPatchValidator to categorize
validation issues in contract patches. They provide type-safe
identification of validation errors and warnings.

Error Code Categories:
    - List Operations: Duplicate detection within add lists
    - Descriptor/Behavior: Behavior patch consistency issues
    - Identity: Contract identity field issues
    - Profile: Profile reference format issues
    - File I/O: File access and parsing issues
    - Validation: General validation errors

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - ContractPatchValidator: The validator that uses these codes

.. versionadded:: 0.4.0
"""

from enum import Enum


class EnumPatchValidationErrorCode(str, Enum):
    """Error codes for contract patch validation.

    These codes categorize the types of issues that can be detected
    during contract patch validation. They are used in validation
    results to provide machine-readable issue identification.

    Attributes:
        DUPLICATE_LIST_ENTRIES: Duplicate items within an add list
        EMPTY_DESCRIPTOR_PATCH: Behavior patch (descriptor field) with no overrides
        PURITY_IDEMPOTENT_MISMATCH: Conflicting purity/idempotent settings
        NEW_CONTRACT_IDENTITY: Informational - new contract identity declared
        NON_STANDARD_PROFILE_NAME: Profile name doesn't follow conventions
        NON_STANDARD_VERSION_FORMAT: Version string format is non-standard
        FILE_NOT_FOUND: File does not exist
        FILE_READ_ERROR: File could not be read
        UNEXPECTED_EXTENSION: File has unexpected extension
        YAML_VALIDATION_ERROR: YAML parsing or validation error
        PYDANTIC_VALIDATION_ERROR: Pydantic model validation error

    Example:
        >>> from omnibase_core.enums import EnumPatchValidationErrorCode
        >>> code = EnumPatchValidationErrorCode.DUPLICATE_LIST_ENTRIES
        >>> result.add_error("Duplicate handler found", code=code.value)
    """

    # List operation errors
    DUPLICATE_LIST_ENTRIES = "DUPLICATE_LIST_ENTRIES"
    """Duplicate items found within an add list (e.g., handlers__add)."""

    # Descriptor/Behavior errors
    EMPTY_DESCRIPTOR_PATCH = "EMPTY_DESCRIPTOR_PATCH"
    """Behavior patch (descriptor field) is present but has no overrides."""

    PURITY_IDEMPOTENT_MISMATCH = "PURITY_IDEMPOTENT_MISMATCH"
    """Conflicting purity='pure' with idempotent=False settings."""

    # Identity errors
    NEW_CONTRACT_IDENTITY = "NEW_CONTRACT_IDENTITY"
    """Informational: Patch declares a new contract identity (name + version)."""

    # Profile reference errors
    NON_STANDARD_PROFILE_NAME = "NON_STANDARD_PROFILE_NAME"
    """Profile name doesn't follow lowercase_with_underscores convention."""

    NON_STANDARD_VERSION_FORMAT = "NON_STANDARD_VERSION_FORMAT"
    """Version string format is non-standard (expected semver-like)."""

    # File I/O errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    """The specified file does not exist."""

    FILE_READ_ERROR = "FILE_READ_ERROR"
    """The file could not be read (I/O error)."""

    UNEXPECTED_EXTENSION = "UNEXPECTED_EXTENSION"
    """File has unexpected extension (expected .yaml or .yml)."""

    # Validation errors
    YAML_VALIDATION_ERROR = "YAML_VALIDATION_ERROR"
    """YAML parsing or validation error occurred."""

    PYDANTIC_VALIDATION_ERROR = "PYDANTIC_VALIDATION_ERROR"
    """Pydantic model validation error occurred."""
