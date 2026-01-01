"""
Workflow state snapshot model.

Frozen Pydantic model for workflow state serialization and replay.
Follows ONEX one-model-per-file architecture.

Immutability Considerations:
    This model uses ConfigDict(frozen=True) to prevent field reassignment.
    Python's frozen Pydantic models have inherent limitations with mutable containers:

    1. **completed_step_ids/failed_step_ids**: Uses tuple[UUID, ...] for true immutability.
       Tuples are immutable in Python, ensuring the step ID collections cannot be modified
       after snapshot creation.

    2. **context field**: Uses dict[str, Any] which is mutable by Python design.
       The dict container itself cannot be reassigned (frozen), but its contents
       CAN still be modified.

       Current contract: Callers MUST NOT mutate context after snapshot creation.
       Workflow executors should create new snapshots with new context dicts rather
       than modifying existing context.

    This design uses truly immutable tuples for step IDs while accepting documented
    contracts for the context dict where full immutability would be too restrictive.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from typing import ClassVar, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.types.type_workflow_context import WorkflowContextType

WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION: int = 1
"""Current schema version for ModelWorkflowStateSnapshot.

Increment when making breaking changes to the snapshot structure.
See class docstring "Schema Versioning" for version strategy.
"""

# Context size validation limits (configurable via class attributes)
CONTEXT_MAX_KEYS: int = 100
"""Maximum recommended number of keys in context dict (default: 100)."""

CONTEXT_MAX_SIZE_BYTES: int = 1024 * 1024  # 1MB
"""Maximum recommended serialized size of context dict in bytes (default: 1MB)."""

CONTEXT_MAX_NESTING_DEPTH: int = 5
"""Maximum recommended nesting depth of context dict (default: 5 levels)."""

# Environment variable for strict context size enforcement
CONTEXT_SIZE_STRICT_MODE_ENV: str = "ONEX_CONTEXT_SIZE_STRICT"
"""Environment variable name for enabling strict context size enforcement.

When set to '1', 'true', or 'yes' (case-insensitive), validate_context_size()
will raise ModelOnexError when limits are exceeded instead of returning warnings.
"""

# Environment variable for automatic context size warning on snapshot creation
CONTEXT_SIZE_WARN_ON_CREATE_ENV: str = "ONEX_CONTEXT_SIZE_WARN_ON_CREATE"
"""Environment variable to enable context size warnings on snapshot creation.

When set to '1', 'true', or 'yes' (case-insensitive), snapshot creation will
automatically validate context size and log warnings if limits are exceeded.

This is a non-blocking validation that logs warnings but does not raise errors
by default, allowing existing code to continue functioning while alerting
developers to potential context size issues.

The validation respects CONTEXT_MAX_KEYS, CONTEXT_MAX_SIZE_BYTES, and
CONTEXT_MAX_NESTING_DEPTH limits, calling validate_context_size() internally.

Example:
    Set in environment to enable::

        export ONEX_CONTEXT_SIZE_WARN_ON_CREATE=1

    Or in Python before creating snapshots::

        import os
        os.environ["ONEX_CONTEXT_SIZE_WARN_ON_CREATE"] = "true"
"""


class ModelWorkflowStateSnapshot(BaseModel):
    """
    Immutable workflow state snapshot for state serialization.

    Enables workflow state to be snapshotted and restored for:
    - Workflow replay and debugging
    - State persistence across restarts
    - Testing and verification

    Attributes:
        schema_version: Schema version for deserialization and migration support.
            Increment when making breaking changes to the snapshot structure.
        workflow_id: Unique workflow execution ID.
        current_step_index: Index of current step being executed.
        completed_step_ids: Tuple of completed step UUIDs (immutable).
        failed_step_ids: Tuple of failed step UUIDs (immutable).
        context: Workflow execution context data. Uses dict[str, Any] to support
            flexible context structures that vary per workflow implementation.
            **WARNING**: While the context field cannot be reassigned, the dict
            contents are still mutable. Callers MUST NOT modify context after
            snapshot creation to maintain workflow purity.
        created_at: Timestamp when snapshot was created.

    Immutability Contract:
        - **Guaranteed immutable**: workflow_id (UUID | None), current_step_index (int),
          created_at (datetime), completed_step_ids (tuple), failed_step_ids (tuple)
        - **Contractually immutable**: context (dict) - contents can be modified but MUST NOT be
        - Field reassignment is blocked by frozen=True
        - Workflow executors MUST create new snapshots rather than mutating existing ones
        - Extra fields are rejected (extra="forbid")

    Context Size Limits:
        The context dict has no enforced size limit, but recommended limits are:
        - **Max keys**: 100 (for performance during serialization/deserialization)
        - **Max total size**: 1MB serialized (for efficient storage and transfer)
        - **Max nesting depth**: 5 levels (for readability and debugging)
        Exceeding these limits may cause performance degradation during workflow
        replay and state persistence operations.

    Automatic Context Size Validation:
        When the environment variable ONEX_CONTEXT_SIZE_WARN_ON_CREATE is set to
        '1', 'true', or 'yes', snapshot creation automatically validates context
        size and logs warnings if limits are exceeded. This is a non-blocking
        validation that does not raise errors by default, allowing existing code
        to continue functioning while alerting developers to potential issues.

        To enable::

            export ONEX_CONTEXT_SIZE_WARN_ON_CREATE=1

        When enabled, the model_validator calls validate_context_size() and emits
        structured log warnings with workflow_id and specific limit violations.

    PII Handling:
        **WARNING**: The context dict may contain sensitive data. When storing or
        transmitting workflow snapshots:
        - **Never log** context contents at INFO level or below
        - **Sanitize** before persisting to external storage or logs using
          ``sanitize_context_for_logging()``
        - **Encrypt** at rest if context may contain PII (user data, credentials)
        - **Audit** context keys before serialization in production

        Use the ``sanitize_context_for_logging()`` class method to redact common
        PII patterns from context data before logging. Default patterns include:
        - Email addresses
        - Phone numbers (US formats)
        - Social Security Numbers
        - Credit card numbers
        - IPv4 and IPv6 addresses
        - API keys (Stripe, AWS, GitHub, Slack, generic)

        **UUID Redaction (Opt-In)**: UUIDs/GUIDs are NOT redacted by default because
        they are often system-generated identifiers (workflow_id, step_id,
        correlation_id) useful for debugging and tracing. To redact UUIDs, pass
        ``redact_uuids=True`` to ``sanitize_context_for_logging()``.

        See method docstring for customization options.

        Workflow implementations should define clear policies for what data types
        are allowed in context to prevent accidental PII exposure.

    Schema Versioning:
        The schema_version field enables version-aware deserialization and migration.
        Version strategy:
        - **1** (current): Initial schema with core workflow state fields
        - Future versions increment when adding/removing/changing field semantics
        - Deserialization code should check schema_version and migrate as needed
        - Breaking changes require version increment with documented upgrade steps

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it thread-safe
        for concurrent read access from multiple threads or async tasks. However:

        - **Safe**: Reading any field from multiple threads simultaneously
        - **Safe**: Passing snapshots between threads without synchronization
        - **WARNING**: Do NOT mutate dict contents - this violates the immutability
          contract and could cause race conditions

        For state management in NodeOrchestrator, note that while snapshots themselves
        are thread-safe, the NodeOrchestrator instance that creates/restores them is
        NOT thread-safe. See docs/guides/THREADING.md for details.

    Example:
        >>> from uuid import uuid4
        >>> workflow_id = uuid4()
        >>> step1_id = uuid4()
        >>> step2_id = uuid4()
        >>> snapshot = ModelWorkflowStateSnapshot(
        ...     workflow_id=workflow_id,
        ...     current_step_index=2,
        ...     completed_step_ids=(step1_id,),
        ...     failed_step_ids=(step2_id,),
        ...     context={"retry_count": 1},
        ... )
        >>> snapshot.current_step_index
        2

    Warning:
        Do NOT mutate context after creation::

            # WRONG - violates immutability contract
            snapshot.context["new_key"] = "value"

            # CORRECT - create new snapshot with updated values
            new_context = {**snapshot.context, "new_key": "value"}
            new_completed = (*snapshot.completed_step_ids, new_step_id)
            new_snapshot = ModelWorkflowStateSnapshot(
                workflow_id=snapshot.workflow_id,
                current_step_index=snapshot.current_step_index + 1,
                completed_step_ids=new_completed,
                failed_step_ids=snapshot.failed_step_ids,
                context=new_context,
            )
    """

    # -------------------------------------------------------------------------
    # ConfigDict Explanation:
    # -------------------------------------------------------------------------
    # - frozen=True: Prevents field reassignment after construction, providing
    #   immutability at the Pydantic level. Note: This is convention-based for
    #   mutable containers like dict - the context dict contents can still be
    #   modified via context["key"] = value. See "Immutability Considerations"
    #   in the module docstring and ADR-002 for the design rationale.
    #
    # - extra="forbid": Rejects extra fields during validation, ensuring strict
    #   schema compliance and preventing accidental data injection.
    #
    # - from_attributes=True: Required for pytest-xdist parallel test execution.
    #   When tests run across parallel workers, each worker imports classes
    #   independently, causing class identity to differ:
    #       id(ModelWorkflowStateSnapshot) in Worker A !=
    #       id(ModelWorkflowStateSnapshot) in Worker B
    #
    #   Without from_attributes=True, Pydantic's default isinstance() validation
    #   rejects already-valid instances because class identity differs. This
    #   setting enables attribute-based validation instead, allowing Pydantic
    #   to accept objects with matching attributes regardless of class identity.
    #
    #   Technical details:
    #   - Default Pydantic validation uses isinstance() which checks class identity
    #   - from_attributes=True enables ORM-style attribute extraction
    #   - Essential for immutable value objects where equality = data, not class
    #
    #   See CLAUDE.md section "Pydantic from_attributes=True for Value Objects"
    #   for the project-wide pattern and additional affected models.
    # -------------------------------------------------------------------------
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Common PII patterns to redact from context data.
    # Each tuple contains (regex_pattern, replacement_string).
    # Patterns are applied in order; more specific patterns should come first.
    _PII_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # Email addresses (most common PII in workflows)
        (r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b", "[EMAIL_REDACTED]"),
        # Credit card numbers (13-19 digits, optionally grouped by 4)
        # Must come before phone numbers to avoid partial matches
        (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CREDIT_CARD_REDACTED]"),
        # US Phone numbers (various formats including +1, parentheses, dashes, dots, spaces)
        # Matches: +1-555-123-4567, (555) 123-4567, 555.123.4567, 5551234567, etc.
        # (?<!\d) prevents matching digit sequences embedded in larger numbers (like UUIDs)
        (
            r"(?<!\d)(?:\+1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "[PHONE_REDACTED]",
        ),
        # US Social Security Numbers (XXX-XX-XXXX or XXXXXXXXX)
        (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[SSN_REDACTED]"),
        # IP addresses (v4)
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]"),
        # IPv6 addresses (full and compressed forms)
        # Matches: 2001:0db8:85a3:0000:0000:8a2e:0370:7334, ::1, fe80::1, 2001:db8::1, etc.
        # Uses lookahead/lookbehind instead of \b to handle :: correctly
        (
            r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"  # Full form (8 groups)
            r"|(?<![0-9a-fA-F:])::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b"  # Leading :: (::1, ::ffff:x)
            r"|\b(?:[0-9a-fA-F]{1,4}:)+:(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}\b"  # Middle :: (2001:db8::1)
            r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:(?![0-9a-fA-F])"  # Trailing :: (2001:db8::)
            r"|(?<![0-9a-fA-F:])::(?![0-9a-fA-F:])",  # Just :: (unspecified)
            "[IPV6_REDACTED]",
        ),
        # API keys (common formats: prefix + alphanumeric, or long hex/base64 strings)
        # Matches: sk_live_abc123, api_key_xyz789, AKIA..., ghp_..., etc.
        (
            r"\b(?:sk_(?:live|test)_[a-zA-Z0-9]{24,})\b"  # Stripe keys
            r"|\b(?:pk_(?:live|test)_[a-zA-Z0-9]{24,})\b"  # Stripe public keys
            r"|\b(?:AKIA[0-9A-Z]{16})\b"  # AWS access keys
            r"|\b(?:ghp_[a-zA-Z0-9]{36})\b"  # GitHub PAT
            r"|\b(?:gho_[a-zA-Z0-9]{36})\b"  # GitHub OAuth
            r"|\b(?:github_pat_[a-zA-Z0-9_]{22,})\b"  # GitHub fine-grained PAT
            r"|\b(?:xox[baprs]-[a-zA-Z0-9-]{10,})\b"  # Slack tokens
            r"|\b(?:api[_-]?key[_-]?[a-zA-Z0-9]{20,})\b",  # Generic api_key prefix
            "[API_KEY_REDACTED]",
        ),
    ]

    # UUID pattern is SEPARATE from default PII patterns (opt-in redaction).
    # UUIDs are often NOT PII - they may be system-generated identifiers like
    # workflow_id, step_id, correlation_id, etc. that are useful for debugging.
    # Only redact UUIDs when they specifically identify users/sessions in your context.
    # Matches: 550e8400-e29b-41d4-a716-446655440000
    _UUID_PATTERN: ClassVar[tuple[str, str]] = (
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        "[UUID_REDACTED]",
    )

    # Schema version for migration support. Increment when making breaking changes.
    # See "Schema Versioning" in class docstring for version strategy.
    schema_version: int = Field(
        default=WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
        ge=1,
        description="Schema version for deserialization and migration (current: 1)",
    )
    workflow_id: UUID | None = Field(default=None, description="Workflow execution ID")
    current_step_index: int = Field(
        default=0,
        ge=0,
        description="Current step index (must be non-negative)",
    )
    completed_step_ids: tuple[UUID, ...] = Field(
        default=(), description="Completed step IDs (immutable tuple)"
    )
    failed_step_ids: tuple[UUID, ...] = Field(
        default=(), description="Failed step IDs (immutable tuple)"
    )
    context: WorkflowContextType = Field(
        default_factory=dict,
        description="Workflow context - flexible runtime state storage",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Snapshot creation time",
    )

    @model_validator(mode="after")
    def _validate_context_size_on_create(self) -> Self:
        """Optionally validate context size on snapshot creation.

        When ONEX_CONTEXT_SIZE_WARN_ON_CREATE environment variable is set to
        '1', 'true', or 'yes' (case-insensitive), this validator calls
        validate_context_size() and logs warnings if limits are exceeded.

        This is a non-blocking validation that does not raise errors by default,
        allowing existing code to continue functioning while alerting developers
        to potential context size issues during development and testing.

        The validation respects the configured limits:
        - CONTEXT_MAX_KEYS (default: 100)
        - CONTEXT_MAX_SIZE_BYTES (default: 1MB)
        - CONTEXT_MAX_NESTING_DEPTH (default: 5)

        Returns:
            Self: The validated model instance (unchanged).

        Note:
            Warnings are emitted via structured logging with workflow_id context.
            Enable strict mode with ONEX_CONTEXT_SIZE_STRICT for error enforcement.
        """
        warn_on_create = os.getenv(CONTEXT_SIZE_WARN_ON_CREATE_ENV, "").lower() in (
            "1",
            "true",
            "yes",
        )
        if warn_on_create:
            # Use enforce=False to get warnings without raising errors
            _is_valid, warnings = self.__class__.validate_context_size(
                self.context, enforce=False
            )
            if warnings:
                from omnibase_core.enums.enum_log_level import EnumLogLevel
                from omnibase_core.logging import emit_log_event_sync

                emit_log_event_sync(
                    EnumLogLevel.WARNING,
                    f"Context size warnings during snapshot creation: {'; '.join(warnings)}",
                    {
                        "workflow_id": str(self.workflow_id)
                        if self.workflow_id
                        else None,
                        "warnings": warnings,
                    },
                )
        return self

    @classmethod
    def create_initial(
        cls, workflow_id: UUID | None = None
    ) -> ModelWorkflowStateSnapshot:
        """
        Create initial empty snapshot.

        Factory method for creating a new workflow snapshot at the initial state.
        All fields are initialized to their defaults.

        Args:
            workflow_id: Optional workflow execution ID.

        Returns:
            ModelWorkflowStateSnapshot initialized with the given workflow_id and
            default values for all other fields.

        Example:
            >>> from uuid import uuid4
            >>> snapshot = ModelWorkflowStateSnapshot.create_initial(uuid4())
            >>> snapshot.current_step_index
            0
            >>> snapshot.completed_step_ids
            ()
            >>> snapshot.failed_step_ids
            ()
        """
        return cls(workflow_id=workflow_id)

    @classmethod
    def sanitize_context_for_logging(
        cls,
        context: WorkflowContextType,
        additional_patterns: list[tuple[str, str]] | None = None,
        *,
        redact_keys: list[str] | None = None,
        redact_uuids: bool = False,
    ) -> WorkflowContextType:
        """
        Sanitize context dict for safe logging by redacting PII patterns.

        This method creates a deep copy of the context dictionary with common
        PII patterns (email, phone, SSN, credit card, IP address) redacted from
        string values. Use this method before logging or exposing context data
        to prevent accidental PII exposure.

        Args:
            context: The context dictionary to sanitize.
            additional_patterns: Optional list of (regex_pattern, replacement) tuples
                to apply in addition to the default PII patterns. Custom patterns
                are applied after default patterns.
            redact_keys: Optional list of key names to fully redact. If a key matches
                (case-insensitive), its entire value is replaced with "[REDACTED]".
                Useful for known sensitive fields like "password", "api_key", etc.
            redact_uuids: If True, also redact UUIDs/GUIDs from string values.
                Default is False because UUIDs are often NOT PII - they may be
                system-generated identifiers (workflow_id, step_id, correlation_id)
                that are useful for debugging and tracing. Only enable this when
                UUIDs in your context specifically identify users or sessions.

        Returns:
            A new dict with PII patterns redacted. The original context is not modified.

        Example:
            >>> context = {
            ...     "user_email": "john.doe@example.com",
            ...     "phone": "555-123-4567",
            ...     "ssn": "123-45-6789",
            ...     "password": "secret123",
            ...     "nested": {"email": "nested@test.com"},
            ... }
            >>> safe = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            ...     context,
            ...     redact_keys=["password"],
            ... )
            >>> safe["user_email"]
            '[EMAIL_REDACTED]'
            >>> safe["phone"]
            '[PHONE_REDACTED]'
            >>> safe["ssn"]
            '[SSN_REDACTED]'
            >>> safe["password"]
            '[REDACTED]'
            >>> safe["nested"]["email"]
            '[EMAIL_REDACTED]'

        Example with UUID redaction:
            >>> context = {"user_id": "550e8400-e29b-41d4-a716-446655440000"}
            >>> # Without redact_uuids (default) - UUID preserved for debugging
            >>> safe = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
            >>> safe["user_id"]
            '550e8400-e29b-41d4-a716-446655440000'
            >>> # With redact_uuids=True - UUID redacted
            >>> safe = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            ...     context, redact_uuids=True
            ... )
            >>> safe["user_id"]
            '[UUID_REDACTED]'

        Note:
            - This method performs recursive sanitization on nested dicts and lists.
            - Non-string values (int, float, bool, None, UUID, datetime) are preserved.
            - The method is designed to be conservative; some false positives may occur
              (e.g., numbers that look like phone numbers). When in doubt, use
              ``redact_keys`` for known sensitive fields.
            - For production systems, consider defining workflow-specific sanitization
              policies and using ``additional_patterns`` to extend coverage.
            - UUID redaction is opt-in (``redact_uuids=False`` by default) because
              UUIDs are typically system-generated identifiers useful for debugging,
              not personally identifiable information.
        """
        # Build pattern list: start with default PII patterns
        patterns: list[tuple[str, str]] = list(cls._PII_PATTERNS)
        # Optionally include UUID pattern
        if redact_uuids:
            patterns.append(cls._UUID_PATTERN)
        # Add any custom patterns
        if additional_patterns:
            patterns.extend(additional_patterns)
        redact_keys_lower = {k.lower() for k in (redact_keys or [])}

        def _sanitize_value(value: object, key: str | None = None) -> object:
            """Recursively sanitize a value."""
            # Check if this key should be fully redacted
            if key is not None and key.lower() in redact_keys_lower:
                return "[REDACTED]"

            if isinstance(value, str):
                result = value
                for pattern, replacement in patterns:
                    result = re.sub(pattern, replacement, result)
                return result
            elif isinstance(value, dict):
                return {k: _sanitize_value(v, k) for k, v in value.items()}
            elif isinstance(value, list):
                return [_sanitize_value(item) for item in value]
            elif isinstance(value, tuple):
                return tuple(_sanitize_value(item) for item in value)
            # Preserve other types (int, float, bool, None, UUID, datetime, etc.)
            return value

        # Cast is safe because we know context is a dict and _sanitize_value preserves dict structure
        result = _sanitize_value(context)
        assert isinstance(result, dict)
        return result

    @classmethod
    def validate_no_pii(
        cls,
        context: WorkflowContextType,
        *,
        check_uuids: bool = False,
        additional_patterns: list[tuple[str, str]] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate that context contains no PII patterns, optionally raising on detection.

        This method scans the context dict for common PII patterns and returns
        a validation result. Use this for strict compliance scenarios where
        PII must not be present in workflow context data.

        Unlike ``sanitize_context_for_logging()`` which redacts PII, this method
        only detects and reports PII without modifying the context.

        Args:
            context: The context dictionary to validate.
            check_uuids: If True, also check for UUID patterns. Default is False
                because UUIDs are often NOT PII - they may be system-generated
                identifiers useful for debugging.
            additional_patterns: Optional list of (regex_pattern, label) tuples
                to check in addition to default PII patterns. The label is used
                in the returned violation messages.

        Returns:
            A tuple of (is_valid, violations) where:
            - is_valid: True if no PII patterns detected, False otherwise
            - violations: List of violation messages describing detected PII

        Example:
            >>> context = {"email": "user@example.com", "name": "John"}
            >>> is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
            >>> is_valid
            False
            >>> violations
            ['Detected PII pattern (EMAIL) at key: email']

        Example with strict enforcement:
            >>> context = {"phone": "555-123-4567"}
            >>> is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
            >>> if not is_valid:
            ...     raise ValueError(f"PII detected: {violations}")

        Note:
            - This method performs recursive scanning on nested dicts and lists.
            - Only string values are scanned; other types are ignored.
            - Pattern detection uses the same patterns as ``sanitize_context_for_logging()``.
            - For audit logging, consider using both methods: validate first, then
              sanitize before logging if PII is found.
        """
        # Build pattern list with labels for reporting
        pattern_labels: list[tuple[str, str, str]] = [
            (r"\b[\w.+-]+@[\w.-]+\.\w{2,}\b", "EMAIL", "[EMAIL_REDACTED]"),
            (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "CREDIT_CARD", "[CREDIT_CARD_REDACTED]"),
            (
                r"(?<!\d)(?:\+1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b",
                "PHONE",
                "[PHONE_REDACTED]",
            ),
            (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "SSN", "[SSN_REDACTED]"),
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IPV4", "[IP_REDACTED]"),
            (
                r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
                r"|(?<![0-9a-fA-F:])::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b"
                r"|\b(?:[0-9a-fA-F]{1,4}:)+:(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}\b"
                r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:(?![0-9a-fA-F])"
                r"|(?<![0-9a-fA-F:])::(?![0-9a-fA-F:])",
                "IPV6",
                "[IPV6_REDACTED]",
            ),
            (
                r"\b(?:sk_(?:live|test)_[a-zA-Z0-9]{24,})\b"
                r"|\b(?:pk_(?:live|test)_[a-zA-Z0-9]{24,})\b"
                r"|\b(?:AKIA[0-9A-Z]{16})\b"
                r"|\b(?:ghp_[a-zA-Z0-9]{36})\b"
                r"|\b(?:gho_[a-zA-Z0-9]{36})\b"
                r"|\b(?:github_pat_[a-zA-Z0-9_]{22,})\b"
                r"|\b(?:xox[baprs]-[a-zA-Z0-9-]{10,})\b"
                r"|\b(?:api[_-]?key[_-]?[a-zA-Z0-9]{20,})\b",
                "API_KEY",
                "[API_KEY_REDACTED]",
            ),
        ]

        # Optionally include UUID pattern
        if check_uuids:
            pattern_labels.append(
                (
                    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
                    "UUID",
                    "[UUID_REDACTED]",
                )
            )

        # Add any custom patterns
        if additional_patterns:
            for pattern, label in additional_patterns:
                pattern_labels.append((pattern, label, f"[{label}_REDACTED]"))

        violations: list[str] = []

        def _scan_value(value: object, path: str) -> None:
            """Recursively scan a value for PII patterns."""
            if isinstance(value, str):
                for pattern, label, _replacement in pattern_labels:
                    if re.search(pattern, value):
                        violations.append(
                            f"Detected PII pattern ({label}) at path: {path}"
                        )
                        break  # Only report first match per value
            elif isinstance(value, dict):
                for k, v in value.items():
                    new_path = f"{path}.{k}" if path else k
                    _scan_value(v, new_path)
            elif isinstance(value, (list, tuple)):
                for i, item in enumerate(value):
                    _scan_value(item, f"{path}[{i}]")
            # Other types (int, float, bool, None, UUID, datetime) are not scanned

        _scan_value(context, "")

        return len(violations) == 0, violations

    @classmethod
    def validate_context_size(
        cls,
        context: WorkflowContextType,
        *,
        max_keys: int = CONTEXT_MAX_KEYS,
        max_size_bytes: int = CONTEXT_MAX_SIZE_BYTES,
        max_depth: int = CONTEXT_MAX_NESTING_DEPTH,
        enforce: bool | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate context dict against size limits.

        This method checks the context dict against configurable size limits
        and returns validation status along with any warning messages.

        Args:
            context: The context dictionary to validate.
            max_keys: Maximum allowed number of keys (default: CONTEXT_MAX_KEYS = 100).
            max_size_bytes: Maximum allowed serialized size in bytes
                (default: CONTEXT_MAX_SIZE_BYTES = 1MB).
            max_depth: Maximum allowed nesting depth
                (default: CONTEXT_MAX_NESTING_DEPTH = 5).
            enforce: If True, raises ModelOnexError when limits exceeded.
                If False, only returns warnings. If None (default), checks
                ONEX_CONTEXT_SIZE_STRICT environment variable for enforcement.

        Returns:
            A tuple of (is_valid, warnings) where:
            - is_valid: True if all limits are satisfied, False otherwise
            - warnings: List of warning messages for any exceeded limits

        Raises:
            ModelOnexError: When enforce=True (or env var set) and limits exceeded.

        Example:
            >>> context = {"key1": "value1", "key2": {"nested": "value"}}
            >>> is_valid, warnings = ModelWorkflowStateSnapshot.validate_context_size(
            ...     context,
            ...     max_keys=10,
            ...     max_size_bytes=1024,
            ...     max_depth=3,
            ... )
            >>> is_valid
            True
            >>> len(warnings)
            0

        Note:
            - Key count includes all keys at all nesting levels
            - Size is calculated using JSON serialization with default encoder
            - For non-serializable values (UUID, datetime), size calculation uses
              string representation which may slightly differ from actual storage
        """
        warnings: list[str] = []

        # Count total keys at all levels
        def _count_keys(obj: object) -> int:
            if isinstance(obj, dict):
                count = len(obj)
                for value in obj.values():
                    count += _count_keys(value)
                return count
            elif isinstance(obj, (list, tuple)):
                return sum(_count_keys(item) for item in obj)
            return 0

        total_keys = _count_keys(context)
        if total_keys > max_keys:
            warnings.append(
                f"Context has {total_keys} keys, exceeds recommended max of {max_keys}"
            )

        # Calculate serialized size
        try:
            serialized = json.dumps(context, default=str)
            size_bytes = len(serialized.encode("utf-8"))
            if size_bytes > max_size_bytes:
                size_kb = size_bytes / 1024
                max_kb = max_size_bytes / 1024
                warnings.append(
                    f"Context size {size_kb:.1f}KB exceeds recommended max of {max_kb:.1f}KB"
                )
        except (TypeError, ValueError) as e:
            warnings.append(f"Context serialization failed: {e}")

        # Check nesting depth
        # NOTE: Depth only increments for dict nesting ({"a": {"b": ...}}).
        # Lists/tuples do NOT increment depth - they are traversed but treated
        # as "flat" containers. This is intentional: a list of 100 items at
        # depth 1 is still depth 1, not depth 100. The concern is deeply nested
        # dicts which make debugging harder, not large flat collections.
        def _max_depth(obj: object, current: int = 0) -> int:
            if isinstance(obj, dict):
                if not obj:
                    return current
                return max(_max_depth(v, current + 1) for v in obj.values())
            elif isinstance(obj, (list, tuple)):
                if not obj:
                    return current
                # Lists/tuples: traverse items but do NOT increment depth
                return max(_max_depth(item, current) for item in obj)
            return current

        depth = _max_depth(context)
        if depth > max_depth:
            warnings.append(
                f"Context nesting depth {depth} exceeds recommended max of {max_depth}"
            )

        # Determine if enforcement is enabled
        strict_mode = enforce
        if strict_mode is None:
            # Fall back to environment variable
            strict_mode = os.getenv(CONTEXT_SIZE_STRICT_MODE_ENV, "").lower() in (
                "1",
                "true",
                "yes",
            )

        if strict_mode and warnings:
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.errors import ModelOnexError

            raise ModelOnexError(
                message=f"Context size validation failed: {'; '.join(warnings)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"warnings": warnings, "context_keys": list(context.keys())},
            )

        return len(warnings) == 0, warnings

    def with_step_completed(
        self,
        step_id: UUID,
        *,
        new_context: WorkflowContextType | None = None,
    ) -> ModelWorkflowStateSnapshot:
        """
        Create a new snapshot with a step marked as completed.

        This is the preferred method for updating workflow state after step completion.
        It creates a new immutable snapshot, preserving the immutability contract.

        Args:
            step_id: The UUID of the completed step.
            new_context: Optional context updates to merge with existing context.

        Returns:
            A new ModelWorkflowStateSnapshot with the step added to completed_step_ids.

        Example:
            >>> from uuid import uuid4
            >>> snapshot = ModelWorkflowStateSnapshot.create_initial(uuid4())
            >>> step_id = uuid4()
            >>> snapshot = snapshot.with_step_completed(step_id)
            >>> step_id in snapshot.completed_step_ids
            True
        """
        updated_context = (
            {**self.context} if new_context is None else {**self.context, **new_context}
        )
        return ModelWorkflowStateSnapshot(
            schema_version=self.schema_version,
            workflow_id=self.workflow_id,
            current_step_index=self.current_step_index + 1,
            completed_step_ids=(*self.completed_step_ids, step_id),
            failed_step_ids=self.failed_step_ids,  # Tuples are immutable, no copy needed
            context=updated_context,
        )

    def with_step_failed(
        self,
        step_id: UUID,
        *,
        new_context: WorkflowContextType | None = None,
    ) -> ModelWorkflowStateSnapshot:
        """
        Create a new snapshot with a step marked as failed.

        This is the preferred method for updating workflow state after step failure.
        It creates a new immutable snapshot, preserving the immutability contract.

        Args:
            step_id: The UUID of the failed step.
            new_context: Optional context updates to merge with existing context.

        Returns:
            A new ModelWorkflowStateSnapshot with the step added to failed_step_ids.

        Example:
            >>> from uuid import uuid4
            >>> snapshot = ModelWorkflowStateSnapshot.create_initial(uuid4())
            >>> step_id = uuid4()
            >>> snapshot = snapshot.with_step_failed(step_id)
            >>> step_id in snapshot.failed_step_ids
            True
        """
        updated_context = (
            {**self.context} if new_context is None else {**self.context, **new_context}
        )
        return ModelWorkflowStateSnapshot(
            schema_version=self.schema_version,
            workflow_id=self.workflow_id,
            current_step_index=self.current_step_index + 1,
            completed_step_ids=self.completed_step_ids,  # Tuples are immutable, no copy needed
            failed_step_ids=(*self.failed_step_ids, step_id),
            context=updated_context,
        )


__all__ = [
    "ModelWorkflowStateSnapshot",
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    "CONTEXT_MAX_KEYS",
    "CONTEXT_MAX_SIZE_BYTES",
    "CONTEXT_MAX_NESTING_DEPTH",
    "CONTEXT_SIZE_STRICT_MODE_ENV",
    "CONTEXT_SIZE_WARN_ON_CREATE_ENV",
]
