"""
NodeCrossRepoValidationOrchestrator - Orchestrator for cross-repo validation.

Wraps the CrossRepoValidationEngine and emits events for:
- Validation run lifecycle (started, completed)
- Violation batches (50 violations per batch)

This enables dashboard integration and deterministic replay from the event stream.

Related ticket: OMN-1776

Key Design Decisions:
    - Orchestrators emit events/intents, NEVER return typed results
    - Violations are batched at 50 per event to manage Kafka message size
    - All events share run_id for correlation
    - Events are Kafka-serializable (frozen, JSON-compatible)
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.events.validation import (
    ModelValidationRunCompletedEvent,
    ModelValidationRunStartedEvent,
    ModelValidationViolationsBatchEvent,
    ModelViolationRecord,
)
from omnibase_core.models.validation.model_cross_repo_validation_orchestrator_result import (
    CrossRepoValidationOrchestratorResult,
)
from omnibase_core.models.validation.model_validation_policy_contract import (
    ModelValidationPolicyContract,
)
from omnibase_core.models.validation.model_violation_baseline import (
    ModelViolationBaseline,
)
from omnibase_core.nodes.node_validation_orchestrator.protocol_event_emitter import (
    ProtocolEventEmitter,
)
from omnibase_core.validation.cross_repo.engine import CrossRepoValidationEngine

__all__ = ["NodeCrossRepoValidationOrchestrator"]

# Default batch size for violation events
DEFAULT_VIOLATIONS_PER_BATCH = 50


class NodeCrossRepoValidationOrchestrator:
    """
    Orchestrator node for cross-repo validation with event emission.

    Wraps the CrossRepoValidationEngine and emits lifecycle events:
    1. ValidationRunStartedEvent - at validation start
    2. ValidationViolationsBatchEvent - for each batch of violations (50/batch)
    3. ValidationRunCompletedEvent - at validation completion

    Events are designed for Kafka streaming and dashboard reconstruction.
    A validation run can be fully replayed from events alone.

    Architecture Note:
        This class does not inherit from NodeOrchestrator because the contract
        specifies ``requires_workflow_definition: false`` - it coordinates a
        single-engine validation rather than a multi-node workflow DAG. It
        follows orchestrator semantics (emit events, no typed results) without
        requiring the workflow execution machinery.

    Thread Safety:
        This orchestrator is stateless with respect to ``validate()`` calls -
        each call uses only local variables and reads immutable instance state.
        Multiple concurrent calls to ``validate()`` are safe. This differs from
        general ONEX node guidance because this class does not inherit from
        NodeOrchestrator and has no mutable request-scoped state.

    Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.cross_repo import load_policy
        >>>
        >>> policy = load_policy(Path("onex_validation_policy.yaml"))
        >>> orchestrator = NodeCrossRepoValidationOrchestrator(policy)
        >>>
        >>> # Run validation (returns events, does not return result)
        >>> result = await orchestrator.validate(
        ...     root=Path("/workspace/omnibase_core"),
        ...     repo_id="omnibase_core",
        ... )
        >>>
        >>> # Inspect emitted events
        >>> print(f"Run ID: {result.run_id}")
        >>> print(f"Valid: {result.is_valid}")
        >>> print(f"Events: {len(result.events)}")
        >>> for event in result.events:
        ...     print(f"  - {event.event_type}")

    .. versionadded:: 0.13.0
        Initial implementation as part of OMN-1776.
    """

    def __init__(
        self,
        policy: ModelValidationPolicyContract,
        *,
        violations_per_batch: int = DEFAULT_VIOLATIONS_PER_BATCH,
        event_emitter: ProtocolEventEmitter | None = None,
    ) -> None:
        """
        Initialize the validation orchestrator.

        Args:
            policy: Validation policy contract to enforce.
            violations_per_batch: Number of violations per batch event (default: 50).
            event_emitter: Optional event emitter for streaming to Kafka.
                If provided, events are emitted as they're created.

        Note:
            This class uses constructor injection rather than container-based DI.
            It does not call super().__init__(container) because it does not inherit
            from NodeOrchestrator - see class docstring for architectural rationale.
        """
        if violations_per_batch < 1:
            # error-ok: Simple boundary validation per CLAUDE.md ValueError guidelines
            raise ValueError(
                f"violations_per_batch must be >= 1, got {violations_per_batch}"
            )
        self._engine = CrossRepoValidationEngine(policy)
        self._policy = policy
        self._violations_per_batch = violations_per_batch
        self._event_emitter = event_emitter

    async def validate(
        self,
        root: Path,
        repo_id: str,  # string-id-ok: human-readable repository identifier
        *,
        rules: list[str] | None = None,
        baseline: ModelViolationBaseline | None = None,
        correlation_id: UUID | None = None,
    ) -> CrossRepoValidationOrchestratorResult:
        """
        Run validation and emit lifecycle events.

        Per ONEX Four-Node Architecture, this orchestrator emits events
        rather than returning typed business results. The validation result
        is encoded in the emitted events.

        Args:
            root: Root directory to validate.
            repo_id: Identifier of the repository being validated.
            rules: Specific rule IDs to run (default: all enabled).
            baseline: Optional baseline for suppressing known violations.
            correlation_id: Optional correlation ID for request tracing.

        Returns:
            CrossRepoValidationOrchestratorResult containing all emitted events.

        Note:
            Exceptions from the validation engine are caught and result in a
            completed event with is_valid=False and error_message set. The
            event lifecycle (started → completed) is always complete.
        """
        run_id = uuid4()
        events: list[
            ModelValidationRunStartedEvent
            | ModelValidationViolationsBatchEvent
            | ModelValidationRunCompletedEvent
        ] = []
        started_at = datetime.now(UTC)

        # Determine enabled rules
        # NOTE(OMN-1776): Empty rules list treated as "use all policy rules" for
        # consistency with rules=None. Explicitly passing [] is a valid way to
        # request default behavior.
        rules_enabled = rules if rules else list(self._policy.rules.keys())
        enabled_rule_ids = tuple(
            rule_id
            for rule_id in rules_enabled
            if rule_id in self._policy.rules and self._policy.rules[rule_id].enabled
        )

        # Emit started event
        started_event = ModelValidationRunStartedEvent.create(
            run_id=run_id,
            repo_id=repo_id,
            root_path=root,
            policy_name=self._policy.policy_id,
            started_at=started_at,
            rules_enabled=enabled_rule_ids,
            baseline_applied=baseline is not None,
            correlation_id=correlation_id,
        )
        events.append(started_event)
        await self._emit(started_event)

        # NOTE(OMN-1776): Custom exception handling used here instead of
        # @standard_error_handling because we must complete the event lifecycle
        # (emit completed event) even when the engine raises an exception. The
        # decorator would propagate the error, breaking the started->completed
        # event guarantee that consumers depend on for replay/reconstruction.
        error_message: str | None = None
        try:
            # Pass the same rules we reported in the started event for consistency.
            # Using list(enabled_rule_ids) ensures the engine validates exactly
            # what we told consumers we would validate.
            result = self._engine.validate(root, list(enabled_rule_ids), baseline)
            issues = result.issues
            is_valid = result.is_valid
            files_processed = (
                (result.metadata.files_processed or 0) if result.metadata else 0
            )
            rules_applied = (
                (result.metadata.rules_applied or 0) if result.metadata else 0
            )
        except Exception as exc:
            # Capture exception - lifecycle must complete
            error_message = f"{type(exc).__name__}: {exc}"
            issues = []
            is_valid = False
            files_processed = 0
            rules_applied = 0

        # Emit violation batches
        violation_batches = self._create_violation_batches(
            run_id=run_id,
            repo_id=repo_id,
            issues=issues,
            correlation_id=correlation_id,
        )
        for batch_event in violation_batches:
            events.append(batch_event)
            await self._emit(batch_event)

        # Calculate counts
        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        error_count = self._count_by_severity(
            issues,
            {EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL},
        )
        warning_count = self._count_by_severity(
            issues,
            {EnumSeverity.WARNING},
        )
        suppressed_count = sum(
            1
            for issue in issues
            if issue.context and issue.context.get("suppressed") == "true"
        )

        # Emit completed event
        completed_event = ModelValidationRunCompletedEvent.create(
            run_id=run_id,
            repo_id=repo_id,
            is_valid=is_valid,
            total_violations=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suppressed_count=suppressed_count,
            files_processed=files_processed,
            rules_applied=rules_applied,
            duration_ms=duration_ms,
            completed_at=completed_at,
            correlation_id=correlation_id,
            error_message=error_message,
        )
        events.append(completed_event)
        await self._emit(completed_event)

        return CrossRepoValidationOrchestratorResult(
            run_id=run_id,
            events=tuple(events),
        )

    def _create_violation_batches(
        self,
        run_id: UUID,
        repo_id: str,  # string-id-ok: human-readable repository identifier
        issues: list[ModelValidationIssue],
        correlation_id: UUID | None,
    ) -> list[ModelValidationViolationsBatchEvent]:
        """
        Create violation batch events from issues.

        Args:
            run_id: Validation run identifier.
            repo_id: Repository identifier.
            issues: List of validation issues.
            correlation_id: Optional correlation ID.

        Returns:
            List of violation batch events.
        """
        if not issues:
            # Emit a single empty batch to indicate no violations
            return [
                ModelValidationViolationsBatchEvent.create(
                    run_id=run_id,
                    repo_id=repo_id,
                    batch_index=0,
                    total_batches=1,
                    violations=(),
                    correlation_id=correlation_id,
                )
            ]

        # Convert issues to violation records
        records = [self._issue_to_record(issue) for issue in issues]

        # Calculate batch count
        total_batches = (
            len(records) + self._violations_per_batch - 1
        ) // self._violations_per_batch

        # Create batches
        batches: list[ModelValidationViolationsBatchEvent] = []
        for i in range(total_batches):
            start_idx = i * self._violations_per_batch
            end_idx = min(start_idx + self._violations_per_batch, len(records))
            batch_records = tuple(records[start_idx:end_idx])

            batch_event = ModelValidationViolationsBatchEvent.create(
                run_id=run_id,
                repo_id=repo_id,
                batch_index=i,
                total_batches=total_batches,
                violations=batch_records,
                correlation_id=correlation_id,
            )
            batches.append(batch_event)

        return batches

    @staticmethod
    def _issue_to_record(issue: ModelValidationIssue) -> ModelViolationRecord:
        """Convert a ModelValidationIssue to a ModelViolationRecord."""
        return ModelViolationRecord(
            severity=issue.severity.value,
            message=issue.message,
            code=issue.code,
            file_path=str(issue.file_path) if issue.file_path else None,
            line_number=issue.line_number,
            rule_name=issue.rule_name,
            fingerprint=issue.context.get("fingerprint") if issue.context else None,
            suppressed=issue.context.get("suppressed") == "true"
            if issue.context
            else False,
        )

    @staticmethod
    def _count_by_severity(
        issues: list[ModelValidationIssue],
        severities: set[EnumSeverity],
    ) -> int:
        """Count issues matching any of the given severities."""
        return sum(1 for issue in issues if issue.severity in severities)

    async def _emit(self, event: object) -> None:
        """Emit an event if emitter is configured."""
        if self._event_emitter:
            await self._event_emitter.emit(event)
