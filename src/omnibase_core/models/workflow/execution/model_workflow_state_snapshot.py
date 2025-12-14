"""
Workflow state snapshot model.

Frozen Pydantic model for workflow state serialization and replay.
Follows ONEX one-model-per-file architecture.

Immutability Considerations:
    This model uses ConfigDict(frozen=True) to prevent field reassignment.
    Python's frozen Pydantic models have inherent limitations with mutable containers:

    1. **completed_step_ids/failed_step_ids**: Uses list[UUID] as the standard type.
       While lists are mutable by nature, the frozen model prevents reassignment.
       Callers should treat these as immutable.

    2. **context field**: Uses dict[str, Any] which is mutable by Python design.
       The dict container itself cannot be reassigned (frozen), but its contents
       CAN still be modified.

       Current contract: Callers MUST NOT mutate context after snapshot creation.
       Workflow executors should create new snapshots with new context dicts rather
       than modifying existing context.

    This design balances practical Pydantic usage with documented contracts
    where full immutability would be too restrictive.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_workflow_context import WorkflowContextType


class ModelWorkflowStateSnapshot(BaseModel):
    """
    Immutable workflow state snapshot for state serialization.

    Enables workflow state to be snapshotted and restored for:
    - Workflow replay and debugging
    - State persistence across restarts
    - Testing and verification

    Attributes:
        workflow_id: Unique workflow execution ID.
        current_step_index: Index of current step being executed.
        completed_step_ids: List of completed step UUIDs.
        failed_step_ids: List of failed step UUIDs.
        context: Workflow execution context data. Uses dict[str, Any] to support
            flexible context structures that vary per workflow implementation.
            **WARNING**: While the context field cannot be reassigned, the dict
            contents are still mutable. Callers MUST NOT modify context after
            snapshot creation to maintain workflow purity.
        created_at: Timestamp when snapshot was created.

    Immutability Contract:
        - **Guaranteed immutable**: workflow_id (UUID | None), current_step_index (int),
          created_at (datetime)
        - **Contractually immutable**: completed_step_ids (list), failed_step_ids (list),
          context (dict)
        - Field reassignment is blocked by frozen=True
        - Workflow executors MUST create new snapshots rather than mutating existing ones
        - Extra fields are rejected (extra="forbid")

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it thread-safe
        for concurrent read access from multiple threads or async tasks. However:

        - **Safe**: Reading any field from multiple threads simultaneously
        - **Safe**: Passing snapshots between threads without synchronization
        - **WARNING**: Do NOT mutate mutable containers (list/dict contents) - this
          violates the immutability contract and could cause race conditions

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
        ...     completed_step_ids=[step1_id],
        ...     failed_step_ids=[step2_id],
        ...     context={"retry_count": 1},
        ... )
        >>> snapshot.current_step_index
        2

    Warning:
        Do NOT mutate context, completed_step_ids, or failed_step_ids after creation::

            # WRONG - violates immutability contract
            snapshot.context["new_key"] = "value"
            snapshot.completed_step_ids.append(new_step_id)

            # CORRECT - create new snapshot with updated values
            new_context = {**snapshot.context, "new_key": "value"}
            new_completed = [*snapshot.completed_step_ids, new_step_id]
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

    workflow_id: UUID | None = Field(default=None, description="Workflow execution ID")
    current_step_index: int = Field(
        default=0,
        ge=0,
        description="Current step index (must be non-negative)",
    )
    completed_step_ids: list[UUID] = Field(
        default_factory=list, description="Completed step IDs"
    )
    failed_step_ids: list[UUID] = Field(
        default_factory=list, description="Failed step IDs"
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
            []
            >>> snapshot.failed_step_ids
            []
        """
        return cls(workflow_id=workflow_id)

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
            completed_step_ids=[*self.completed_step_ids, step_id],
            failed_step_ids=list(self.failed_step_ids),  # Copy to avoid aliasing
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
            completed_step_ids=list(self.completed_step_ids),  # Copy to avoid aliasing
            failed_step_ids=[*self.failed_step_ids, step_id],
            context=updated_context,
        )


__all__ = ["ModelWorkflowStateSnapshot"]
