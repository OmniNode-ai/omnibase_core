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

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPatchValidationErrorCode(StrValueHelper, str, Enum):
    """Error codes for contract patch validation.

    These codes categorize the types of issues that can be detected
    during contract patch validation. They are used in validation
    results to provide machine-readable issue identification.

    All error codes follow the CONTRACT_PATCH_* prefix convention for
    consistent categorization and type-safe identification per PR #289.

    Attributes:
        CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES: Duplicate items within an add list
        CONTRACT_PATCH_EMPTY_DESCRIPTOR: Behavior patch with no overrides
        CONTRACT_PATCH_PURITY_IDEMPOTENT_MISMATCH: Conflicting purity/idempotent settings
        CONTRACT_PATCH_NEW_IDENTITY: Informational - new contract identity declared
        CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME: Profile name doesn't follow conventions
        CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT: Version string format is non-standard
        CONTRACT_PATCH_FILE_NOT_FOUND: File does not exist
        CONTRACT_PATCH_FILE_READ_ERROR: File could not be read
        CONTRACT_PATCH_UNEXPECTED_EXTENSION: File has unexpected extension
        CONTRACT_PATCH_YAML_VALIDATION_ERROR: YAML parsing or validation error
        CONTRACT_PATCH_PYDANTIC_VALIDATION_ERROR: Pydantic model validation error

    Example:
        >>> from omnibase_core.enums import EnumPatchValidationErrorCode
        >>> code = EnumPatchValidationErrorCode.CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES
        >>> result.add_error("Duplicate handler found", code=code.value)
    """

    # List operation errors
    CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES = "CONTRACT_PATCH_DUPLICATE_LIST_ENTRIES"
    """Duplicate items found within an add list (e.g., handlers__add)."""

    # Descriptor/Behavior errors
    CONTRACT_PATCH_EMPTY_DESCRIPTOR = "CONTRACT_PATCH_EMPTY_DESCRIPTOR"
    """Behavior patch (descriptor field) is present but has no overrides."""

    CONTRACT_PATCH_PURITY_IDEMPOTENT_MISMATCH = (
        "CONTRACT_PATCH_PURITY_IDEMPOTENT_MISMATCH"
    )
    """Conflicting purity='pure' with idempotent=False settings."""

    # Identity errors
    CONTRACT_PATCH_NEW_IDENTITY = "CONTRACT_PATCH_NEW_IDENTITY"
    """Informational: Patch declares a new contract identity (name + version)."""

    # Profile reference errors
    CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME = (
        "CONTRACT_PATCH_NON_STANDARD_PROFILE_NAME"
    )
    """Profile name doesn't follow lowercase_with_underscores convention."""

    CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT = (
        "CONTRACT_PATCH_NON_STANDARD_VERSION_FORMAT"
    )
    """Version string format is non-standard (expected semver-like)."""

    # File I/O errors
    CONTRACT_PATCH_FILE_NOT_FOUND = "CONTRACT_PATCH_FILE_NOT_FOUND"
    """The specified file does not exist."""

    CONTRACT_PATCH_FILE_READ_ERROR = "CONTRACT_PATCH_FILE_READ_ERROR"
    """The file could not be read (I/O error)."""

    CONTRACT_PATCH_UNEXPECTED_EXTENSION = "CONTRACT_PATCH_UNEXPECTED_EXTENSION"
    """File has unexpected extension (expected .yaml or .yml)."""

    # Validation errors
    CONTRACT_PATCH_YAML_VALIDATION_ERROR = "CONTRACT_PATCH_YAML_VALIDATION_ERROR"
    """YAML parsing or validation error occurred."""

    CONTRACT_PATCH_PYDANTIC_VALIDATION_ERROR = (
        "CONTRACT_PATCH_PYDANTIC_VALIDATION_ERROR"
    )
    """Pydantic model validation error occurred."""


__all__ = ["EnumPatchValidationErrorCode"]
