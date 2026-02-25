# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelEnvelopeValidationConfig - Configuration for envelope validation strictness.

This model defines the validation mode and options for envelope validation
in the ONEX runtime. Supports strict and lenient validation modes configurable
via environment variable (ONEX_VALIDATION_MODE) or runtime injection.

Architecture:
    - Strict mode: Fail fast on any validation issue, reject malformed envelopes,
      require all optional fields, enforce schema compliance.
    - Lenient mode: Best-effort processing with warnings, auto-generate missing
      correlation IDs, accept partial payloads.

Environment Variable:
    ONEX_VALIDATION_MODE=strict|lenient (default: lenient)

Usage:
    .. code-block:: python

        from omnibase_core.models.validation.model_envelope_validation_config import (
            ModelEnvelopeValidationConfig,
        )

        # From environment variable
        config = ModelEnvelopeValidationConfig.from_env()

        # Explicit strict mode
        config = ModelEnvelopeValidationConfig.strict()

        # Explicit lenient mode
        config = ModelEnvelopeValidationConfig.lenient()

Related:
    - OMN-840: Add configurable validation strictness levels
    - OMN-817: Minimal envelope validation before dispatch (PR #35)
    - EnvelopeValidator: Validator that consumes this config
"""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_pipeline_validation_mode import EnumPipelineValidationMode

__all__ = ["ModelEnvelopeValidationConfig"]

# Environment variable name for configuring validation mode
ENV_VALIDATION_MODE = "ONEX_VALIDATION_MODE"

# Default validation mode when env var is not set
DEFAULT_VALIDATION_MODE = EnumPipelineValidationMode.LENIENT


class ModelEnvelopeValidationConfig(BaseModel):
    """
    Configuration model for envelope validation strictness.

    Controls how the EnvelopeValidator behaves when it encounters validation
    issues in envelopes before dispatch.

    Attributes:
        mode: The validation mode. STRICT fails fast on any issue; LENIENT
            logs warnings but allows processing to continue.
        require_correlation_id: In strict mode, require correlation_id to be
            present. In lenient mode, auto-generate if missing (default: True
            in strict, False in lenient).
        require_all_optional_fields: In strict mode, require all optional
            envelope fields to be present. Default False.
        reject_empty_list_payloads: Reject payloads where list-expecting
            operations receive empty lists. Default True in strict, False in
            lenient.
        validate_payload_schema: Validate payload structure against known
            schemas for operation types. Default True.
        log_warnings: Emit log warnings for validation issues in lenient mode.
            Default True.

    Thread Safety:
        This model uses ``frozen=True`` (immutable after creation). Safe for
        concurrent access. Create separate instances per handler if per-handler
        overrides are needed.

    Example:
        >>> config = ModelEnvelopeValidationConfig.strict()
        >>> config.mode == EnumPipelineValidationMode.STRICT
        True
        >>> config.require_correlation_id
        True

        >>> config = ModelEnvelopeValidationConfig.from_env()
        >>> # Uses ONEX_VALIDATION_MODE env var, defaults to lenient
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    mode: EnumPipelineValidationMode = Field(
        default=DEFAULT_VALIDATION_MODE,
        description="Validation mode: strict (fail fast) or lenient (best-effort with warnings).",
    )

    require_correlation_id: bool = Field(
        default=True,
        description=(
            "Require correlation_id to be present. In lenient mode with this False, "
            "auto-generates missing correlation IDs with a warning."
        ),
    )

    require_all_optional_fields: bool = Field(
        default=False,
        description=(
            "Require all optional envelope fields to be present. "
            "Only enforced in strict mode."
        ),
    )

    reject_empty_list_payloads: bool = Field(
        default=True,
        description=(
            "Reject payloads where list-expecting operations receive empty lists. "
            "In lenient mode, logs a warning instead of rejecting."
        ),
    )

    validate_payload_schema: bool = Field(
        default=True,
        description=(
            "Validate payload structure against known schemas for operation types. "
            "Type coercion warnings are emitted for mismatched but convertible types."
        ),
    )

    log_warnings: bool = Field(
        default=True,
        description=(
            "Emit log warnings for validation issues in lenient mode. "
            "Always True in strict mode (issues raise errors)."
        ),
    )

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> ModelEnvelopeValidationConfig:
        """
        Create configuration from environment variable ONEX_VALIDATION_MODE.

        Reads ONEX_VALIDATION_MODE from the environment. If not set or invalid,
        defaults to lenient mode.

        Returns:
            ModelEnvelopeValidationConfig with mode set from the environment.

        Example:
            >>> import os
            >>> os.environ["ONEX_VALIDATION_MODE"] = "strict"
            >>> config = ModelEnvelopeValidationConfig.from_env()
            >>> config.mode == EnumPipelineValidationMode.STRICT
            True
        """
        raw_mode = os.environ.get(ENV_VALIDATION_MODE, "").strip().lower()

        if raw_mode == EnumPipelineValidationMode.STRICT.value:
            return cls.strict()
        elif raw_mode == EnumPipelineValidationMode.LENIENT.value:
            return cls.lenient()
        else:
            # Default to lenient for unknown or unset values
            return cls.lenient()

    @classmethod
    def strict(cls) -> ModelEnvelopeValidationConfig:
        """
        Create a strict validation configuration.

        Strict mode: Fail fast on any validation issue. Reject malformed envelopes
        immediately. Require all optional fields to be present (when
        require_all_optional_fields=True). Enforce schema compliance.

        Returns:
            ModelEnvelopeValidationConfig configured for strict validation.

        Example:
            >>> config = ModelEnvelopeValidationConfig.strict()
            >>> config.is_strict()
            True
            >>> config.require_correlation_id
            True
        """
        return cls(
            mode=EnumPipelineValidationMode.STRICT,
            require_correlation_id=True,
            require_all_optional_fields=False,
            reject_empty_list_payloads=True,
            validate_payload_schema=True,
            log_warnings=True,
        )

    @classmethod
    def lenient(cls) -> ModelEnvelopeValidationConfig:
        """
        Create a lenient validation configuration.

        Lenient mode: Best-effort processing with warnings. Log validation issues
        but continue processing. Auto-generate missing correlation IDs.
        Accept partial payloads.

        Returns:
            ModelEnvelopeValidationConfig configured for lenient validation.

        Example:
            >>> config = ModelEnvelopeValidationConfig.lenient()
            >>> config.is_lenient()
            True
            >>> config.require_all_optional_fields
            False
        """
        return cls(
            mode=EnumPipelineValidationMode.LENIENT,
            require_correlation_id=False,
            require_all_optional_fields=False,
            reject_empty_list_payloads=False,
            validate_payload_schema=True,
            log_warnings=True,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def is_strict(self) -> bool:
        """
        Check if this configuration enforces strict validation.

        Returns:
            True if mode is STRICT.
        """
        return self.mode == EnumPipelineValidationMode.STRICT

    def is_lenient(self) -> bool:
        """
        Check if this configuration uses lenient (best-effort) validation.

        Returns:
            True if mode is LENIENT.
        """
        return self.mode == EnumPipelineValidationMode.LENIENT

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"ModelEnvelopeValidationConfig["
            f"mode={self.mode.value}, "
            f"require_correlation_id={self.require_correlation_id}, "
            f"reject_empty_list_payloads={self.reject_empty_list_payloads}]"
        )
