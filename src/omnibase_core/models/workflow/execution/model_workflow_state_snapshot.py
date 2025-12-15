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

import re
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_workflow_context import WorkflowContextType

WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION: int = 1
"""Current schema version for ModelWorkflowStateSnapshot.

Increment when making breaking changes to the snapshot structure.
See class docstring "Schema Versioning" for version strategy.
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

    PII Handling:
        **WARNING**: The context dict may contain sensitive data. When storing or
        transmitting workflow snapshots:
        - **Never log** context contents at INFO level or below
        - **Sanitize** before persisting to external storage or logs using
          ``sanitize_context_for_logging()``
        - **Encrypt** at rest if context may contain PII (user data, credentials)
        - **Audit** context keys before serialization in production

        Use the ``sanitize_context_for_logging()`` class method to redact common
        PII patterns (email, phone, SSN, credit card, IP address) from context data
        before logging. See method docstring for customization options.

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

    # from_attributes=True enables attribute-based validation for pytest-xdist compatibility.
    # When tests run across parallel workers, each worker imports classes independently,
    # causing class identity to differ (id(ModelWorkflowStateSnapshot) in Worker A !=
    # id(ModelWorkflowStateSnapshot) in Worker B). Without from_attributes=True, Pydantic
    # rejects already-valid instances because isinstance() checks fail. This setting allows
    # Pydantic to accept objects with matching attributes regardless of class identity.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects" for details.
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
        (
            r"(?:\+1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "[PHONE_REDACTED]",
        ),
        # US Social Security Numbers (XXX-XX-XXXX or XXXXXXXXX)
        (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[SSN_REDACTED]"),
        # IP addresses (v4)
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]"),
    ]

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

        Note:
            - This method performs recursive sanitization on nested dicts and lists.
            - Non-string values (int, float, bool, None, UUID, datetime) are preserved.
            - The method is designed to be conservative; some false positives may occur
              (e.g., numbers that look like phone numbers). When in doubt, use
              ``redact_keys`` for known sensitive fields.
            - For production systems, consider defining workflow-specific sanitization
              policies and using ``additional_patterns`` to extend coverage.
        """
        patterns = cls._PII_PATTERNS + (additional_patterns or [])
        redact_keys_lower = {k.lower() for k in (redact_keys or [])}

        def _sanitize_value(value: Any, key: str | None = None) -> Any:
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
            workflow_id=self.workflow_id,
            current_step_index=self.current_step_index + 1,
            completed_step_ids=self.completed_step_ids,  # Tuples are immutable, no copy needed
            failed_step_ids=(*self.failed_step_ids, step_id),
            context=updated_context,
        )


__all__ = ["ModelWorkflowStateSnapshot", "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION"]
