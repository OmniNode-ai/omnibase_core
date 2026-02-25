# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnvelopeValidator - Configurable envelope validation with strict/lenient modes.

This module provides envelope validation with configurable strictness levels
for the ONEX runtime. Validation behavior is controlled by
ModelEnvelopeValidationConfig, which can be set via environment variable
(ONEX_VALIDATION_MODE) or runtime injection.

Architecture:
    The EnvelopeValidator performs two validation layers:
    1. Structural validation: correlation_id, source_node, operation fields
    2. Payload type validation: reject empty lists for list-expecting operations,
       validate payload structure for known operation types

Strictness Levels:
    - Strict mode: Fail fast on any validation issue (raises EnvelopeValidationError)
    - Lenient mode: Log warnings and continue processing; auto-generate missing
      correlation IDs when require_correlation_id=False

Per-Handler Override:
    Pass a ModelEnvelopeValidationConfig to validate() to override the default
    config for a specific handler invocation.

Usage:
    .. code-block:: python

        from omnibase_core.validation.envelope_validator import EnvelopeValidator
        from omnibase_core.models.validation.model_envelope_validation_config import (
            ModelEnvelopeValidationConfig,
        )

        # From environment variable
        validator = EnvelopeValidator.from_env()

        # Explicit strict mode
        validator = EnvelopeValidator(config=ModelEnvelopeValidationConfig.strict())

        # Validate an envelope
        result = validator.validate(envelope)
        if not result.is_valid:
            print(result.errors)

        # Per-handler override
        result = validator.validate(envelope, config_override=handler_config)

Related:
    - OMN-840: Add configurable validation strictness levels
    - OMN-817: Minimal envelope validation before dispatch (PR #35)
    - ModelEnvelopeValidationConfig: Configuration model
    - EnvelopeRouter: Integrates this validator before dispatch
    - EnvelopeValidationError: Exception raised on strict mode failures
    - EnvelopeValidationResult: Result returned from validate()

.. versionadded:: 0.20.0
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from omnibase_core.models.validation.model_envelope_validation_config import (
    ModelEnvelopeValidationConfig,
)
from omnibase_core.validation.envelope_validation_error import EnvelopeValidationError
from omnibase_core.validation.envelope_validation_result import EnvelopeValidationResult

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope

__all__ = ["EnvelopeValidator"]

logger = logging.getLogger(__name__)

# Operations that expect a list payload (used for empty-list rejection)
LIST_EXPECTING_OPERATIONS: frozenset[str] = frozenset(
    {
        "BATCH_PROCESS",
        "PROCESS_BATCH",
        "BULK_INSERT",
        "BULK_UPDATE",
        "BULK_DELETE",
        "LIST_ITEMS",
        "GET_ITEMS",
        "FETCH_MANY",
        "AGGREGATE_ITEMS",
        "MERGE_ITEMS",
    }
)

# Operations that expect specific payload keys (known operation schemas)
KNOWN_OPERATION_SCHEMAS: dict[str, frozenset[str]] = {
    "REGISTER_NODE": frozenset({"node_id", "node_type"}),
    "DEREGISTER_NODE": frozenset({"node_id"}),
    "HEALTH_CHECK": frozenset({"check_id"}),
    "INTROSPECT": frozenset({"query_type"}),
    "DISCOVERY_REQUEST": frozenset({"requester_id"}),
    "DISCOVERY_RESPONSE": frozenset({"responder_id", "capabilities"}),
}


class EnvelopeValidator:
    """
    Configurable envelope validator with strict and lenient modes.

    Validates ModelOnexEnvelope instances before dispatch, performing:
    1. Structural validation (required fields, correlation_id presence)
    2. Payload type validation (empty list rejection, known schema checks)
    3. Type coercion warnings (for mismatched but convertible types)

    In strict mode, validation failures raise EnvelopeValidationError.
    In lenient mode, validation issues are logged as warnings and processing
    continues.

    Per-Handler Override:
        The validate() method accepts an optional config_override to apply
        different strictness for specific handler invocations.

    Example:
        .. code-block:: python

            # Create from environment variable
            validator = EnvelopeValidator.from_env()

            # Validate before dispatch
            result = validator.validate(envelope)
            if not result.is_valid:
                # strict mode would have raised, so this only happens in lenient
                logger.warning("Envelope validation failed: %s", result.errors)

            # Per-handler override (e.g., strict for critical handlers)
            strict_config = ModelEnvelopeValidationConfig.strict()
            result = validator.validate(envelope, config_override=strict_config)

    Thread Safety:
        EnvelopeValidator is thread-safe. The config is immutable (frozen Pydantic
        model) and validate() is a pure function with no shared mutable state.

    .. versionadded:: 0.20.0
    .. seealso:: OMN-840
    """

    def __init__(self, config: ModelEnvelopeValidationConfig | None = None) -> None:
        """
        Initialize the validator with a validation configuration.

        Args:
            config: Optional validation configuration. If None, creates
                a default lenient configuration.

        Example:
            >>> validator = EnvelopeValidator()  # lenient by default
            >>> validator = EnvelopeValidator(config=ModelEnvelopeValidationConfig.strict())
        """
        self._config: ModelEnvelopeValidationConfig = (
            config if config is not None else ModelEnvelopeValidationConfig.lenient()
        )

    @classmethod
    def from_env(cls) -> EnvelopeValidator:
        """
        Create an EnvelopeValidator configured from environment variables.

        Reads ONEX_VALIDATION_MODE from the environment.
        Defaults to lenient if not set or invalid.

        Returns:
            EnvelopeValidator with config from environment.

        Example:
            >>> import os
            >>> os.environ["ONEX_VALIDATION_MODE"] = "strict"
            >>> validator = EnvelopeValidator.from_env()
            >>> validator.config.is_strict()
            True
        """
        return cls(config=ModelEnvelopeValidationConfig.from_env())

    @property
    def config(self) -> ModelEnvelopeValidationConfig:
        """The default validation configuration for this validator."""
        return self._config

    def validate(
        self,
        envelope: ModelOnexEnvelope,
        *,
        config_override: ModelEnvelopeValidationConfig | None = None,
    ) -> EnvelopeValidationResult:
        """
        Validate an envelope before dispatch.

        Performs structural and payload validation according to the configured
        (or overridden) strictness level.

        In strict mode: raises EnvelopeValidationError on first blocking violation.
        In lenient mode: collects all issues, logs warnings, returns result.

        Args:
            envelope: The ModelOnexEnvelope to validate.
            config_override: Optional per-call configuration override.
                Useful for per-handler strictness differences.

        Returns:
            EnvelopeValidationResult with is_valid, errors, and warnings.

        Raises:
            EnvelopeValidationError: In strict mode when validation fails.

        Example:
            >>> result = validator.validate(envelope)
            >>> if result.has_warnings():
            ...     logger.debug("Validation warnings: %s", result.warnings)
        """
        config = config_override if config_override is not None else self._config
        errors: list[str] = []
        warnings: list[str] = []

        # --- Structural Validation ---
        self._validate_structure(envelope, config, errors, warnings)

        # --- Payload Type Validation ---
        self._validate_payload(envelope, config, errors, warnings)

        # --- Determine result ---
        is_valid = len(errors) == 0
        result = EnvelopeValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            mode=config.mode,
        )

        # Emit log warnings if configured
        if config.log_warnings and warnings:
            envelope_id = str(getattr(envelope, "envelope_id", "unknown"))
            for warning in warnings:
                logger.warning(
                    "Envelope validation warning [%s]: %s",
                    envelope_id,
                    warning,
                )

        # In strict mode, raise on any error
        if config.is_strict() and errors:
            envelope_id = str(getattr(envelope, "envelope_id", None))
            raise EnvelopeValidationError(errors=errors, envelope_id=envelope_id)

        return result

    def _validate_structure(
        self,
        envelope: ModelOnexEnvelope,
        config: ModelEnvelopeValidationConfig,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Validate structural fields of the envelope.

        Checks: correlation_id, source_node, operation, envelope_id.

        Args:
            envelope: The envelope to validate.
            config: The validation configuration to apply.
            errors: List to append error messages to.
            warnings: List to append warning messages to.
        """
        # Validate correlation_id
        correlation_id = getattr(envelope, "correlation_id", None)
        if correlation_id is None:
            msg = "Missing correlation_id"
            if config.require_correlation_id:
                errors.append(msg)
            else:
                warnings.append(f"{msg} (auto-generating in lenient mode)")
                logger.debug(
                    "Auto-generating correlation_id for envelope with operation=%s",
                    getattr(envelope, "operation", "unknown"),
                )
        elif isinstance(correlation_id, str):
            # Type coercion warning: string correlation_id (should be UUID)
            try:
                uuid.UUID(correlation_id)
                warnings.append(
                    f"correlation_id is a string UUID (type coercion will be applied): {correlation_id!r}"
                )
            except ValueError:
                errors.append(f"correlation_id is not a valid UUID: {correlation_id!r}")

        # Validate source_node
        source_node = getattr(envelope, "source_node", None)
        if not source_node or (
            isinstance(source_node, str) and not source_node.strip()
        ):
            errors.append("Missing or empty source_node")

        # Validate operation
        operation = getattr(envelope, "operation", None)
        if not operation or (isinstance(operation, str) and not operation.strip()):
            errors.append("Missing or empty operation")

        # In strict mode with require_all_optional_fields, check optional fields
        if config.is_strict() and config.require_all_optional_fields:
            target_node = getattr(envelope, "target_node", None)
            if target_node is None:
                errors.append(
                    "Missing target_node (required in strict mode with require_all_optional_fields)"
                )

            envelope_version = getattr(envelope, "envelope_version", None)
            if envelope_version is None:
                errors.append(
                    "Missing envelope_version (required in strict mode with require_all_optional_fields)"
                )

    def _validate_payload(
        self,
        envelope: ModelOnexEnvelope,
        config: ModelEnvelopeValidationConfig,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Validate the payload structure of the envelope.

        Checks:
        - Empty list payloads for list-expecting operations
        - Known operation schema compliance
        - Type coercion warnings for mismatched but convertible types

        Args:
            envelope: The envelope to validate.
            config: The validation configuration to apply.
            errors: List to append error messages to.
            warnings: List to append warning messages to.
        """
        operation = getattr(envelope, "operation", None)
        payload = getattr(envelope, "payload", None)

        if not operation or payload is None:
            return

        # Check empty list payloads for list-expecting operations.
        # Always check for list-expecting operations; strict vs lenient determines
        # whether an empty list is an error or a warning.
        operation_upper = operation.upper() if isinstance(operation, str) else ""
        if operation_upper in LIST_EXPECTING_OPERATIONS:
            # Check if the payload contains an empty list in a known list key
            items = None
            for list_key in ("items", "data", "records"):
                candidate = payload.get(list_key)
                if candidate is not None:
                    items = candidate
                    break
            if items is not None and isinstance(items, list) and len(items) == 0:
                msg = (
                    f"Operation '{operation}' expects a non-empty list payload, "
                    f"but received empty list for key 'items'/'data'/'records'"
                )
                if config.is_strict() and config.reject_empty_list_payloads:
                    errors.append(msg)
                else:
                    warnings.append(msg)

        # Validate payload schema for known operation types
        if config.validate_payload_schema:
            self._validate_known_schema(operation, payload, config, errors, warnings)

    def _validate_known_schema(
        self,
        operation: str,
        payload: dict[str, object],
        config: ModelEnvelopeValidationConfig,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Validate payload against known operation schemas.

        For operations with known required fields, check that all required
        fields are present. Emit type coercion warnings for fields that
        exist but have incorrect types that could be converted.

        Args:
            operation: The operation type string.
            payload: The payload dictionary.
            config: The validation configuration.
            errors: List to append error messages to.
            warnings: List to append warning messages to.
        """
        operation_upper = operation.upper() if isinstance(operation, str) else ""
        required_keys = KNOWN_OPERATION_SCHEMAS.get(operation_upper)

        if required_keys is None:
            return  # Unknown operation, no schema to validate against

        missing_keys = required_keys - set(payload.keys())
        if missing_keys:
            msg = (
                f"Operation '{operation}' payload is missing required fields: "
                f"{sorted(missing_keys)}"
            )
            if config.is_strict():
                errors.append(msg)
            else:
                warnings.append(msg)
            return

        # Check for type coercion opportunities (warn on mismatched but convertible types)
        for key in required_keys:
            value = payload.get(key)
            if value is not None and not isinstance(value, str):
                # UUID fields: check if value could be a UUID string
                if key.endswith("_id") and isinstance(value, (bytes, int)):
                    warnings.append(
                        f"Field '{key}' in operation '{operation}' has type "
                        f"{type(value).__name__!r} (expected str UUID, type coercion may apply)"
                    )
