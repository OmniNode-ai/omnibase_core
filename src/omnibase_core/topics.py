# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical wire-format topic names for the ONEX event bus.

Moved from omniclaude/hooks/topics.py in OMN-9335 — this is the permanent home for
cross-repo wire-format topic definitions. Application packages (omniclaude,
omnimarket, etc.) should import from here rather than redefining.

Per OMN-1972, TopicBase values ARE the canonical wire topic names. No environment
prefix is applied. The build_topic() helper validates and returns the canonical
topic name (prefix parameter removed in OMN-5212).
"""

from __future__ import annotations

import re
from enum import StrEnum

from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.models.errors import ModelOnexError

# Valid topic name pattern: alphanumeric segments separated by single dots
# No leading/trailing dots, no consecutive dots, no special characters except dots
_TOPIC_SEGMENT_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Canonical ONEX topic pattern: onex.(cmd|evt|dlq|i*).<service>.<event>.v<N>
_CANONICAL_TOPIC_PATTERN = re.compile(
    r"^onex\.(cmd|evt|dlq|i[a-z0-9_-]*)\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.v\d+$"
)


class TopicBase(StrEnum):
    """Base topic names (without environment prefix).

    All topics follow ONEX canonical format (OMN-1537):
        onex.{kind}.{producer}.{event-name}.v{n}

    Where:
        - kind: cmd, evt, dlq, intent, snapshot
        - producer: service name (omniclaude, omninode, omniintelligence)
        - event-name: kebab-case event name
        - v{n}: version number
    """

    # ==========================================================================
    # omniclaude event topics (hooks → event bus)
    # ==========================================================================
    SESSION_STARTED = "onex.evt.omniclaude.session-started.v1"
    SESSION_ENDED = "onex.evt.omniclaude.session-ended.v1"
    PROMPT_SUBMITTED = "onex.evt.omniclaude.prompt-submitted.v1"
    TOOL_EXECUTED = "onex.evt.omniclaude.tool-executed.v1"
    AGENT_ACTION = "onex.evt.omniclaude.agent-action.v1"
    LEARNING_PATTERN = "onex.evt.omniclaude.learning-pattern.v1"

    # ==========================================================================
    # omninode routing topics (agent routing commands/events)
    # ==========================================================================
    ROUTING_REQUESTED = "onex.cmd.omninode.routing-requested.v1"
    ROUTING_COMPLETED = "onex.evt.omninode.routing-completed.v1"
    ROUTING_FAILED = "onex.evt.omninode.routing-failed.v1"

    # ==========================================================================
    # Cross-service topics (omniclaude → omniintelligence)
    # ==========================================================================
    # Claude hook event topic (consumed by omniintelligence.NodeClaudeHookEventEffect)
    CLAUDE_HOOK_EVENT = "onex.cmd.omniintelligence.claude-hook-event.v1"
    # Tool content topic for pattern learning (OMN-1702)
    TOOL_CONTENT = "onex.cmd.omniintelligence.tool-content.v1"
    # Session outcome: CMD target for intelligence feedback loop (OMN-1735)
    SESSION_OUTCOME_CMD = "onex.cmd.omniintelligence.session-outcome.v1"
    # Session outcome: EVT target for dashboards / monitoring
    SESSION_OUTCOME_EVT = "onex.evt.omniclaude.session-outcome.v1"
    # Utilization scoring: CMD target for LLM-based scoring (OMN-5505)
    UTILIZATION_SCORING_CMD = "onex.cmd.omniintelligence.utilization-scoring.v1"
    # LLM call completed: cost telemetry for omnidash llm_cost_aggregates (OMN-7570)
    LLM_CALL_COMPLETED = "onex.evt.omniintelligence.llm-call-completed.v1"

    # ==========================================================================
    # Hook adapter observability topics (migrated to ONEX format, OMN-1552)
    # ==========================================================================
    AGENT_ACTIONS = "onex.evt.omniclaude.agent-actions.v1"
    PERFORMANCE_METRICS = "onex.evt.omniclaude.performance-metrics.v1"
    TRANSFORMATIONS = "onex.evt.omniclaude.agent-transformation.v1"
    DETECTION_FAILURES = "onex.evt.omniclaude.detection-failure.v1"

    # ==========================================================================
    # Context injection topics (OMN-1403)
    # ==========================================================================
    CONTEXT_RETRIEVAL_REQUESTED = "onex.cmd.omniclaude.context-retrieval-requested.v1"
    CONTEXT_RETRIEVAL_COMPLETED = "onex.evt.omniclaude.context-retrieval-completed.v1"
    CONTEXT_INJECTED = "onex.evt.omniclaude.context-injected.v1"
    # Injection tracking event (OMN-1673 INJECT-004)
    INJECTION_RECORDED = "onex.evt.omniclaude.injection-recorded.v1"

    # ==========================================================================
    # Injection metrics topics (OMN-1889)
    # ==========================================================================
    CONTEXT_UTILIZATION = "onex.evt.omniclaude.context-utilization.v1"
    AGENT_MATCH = "onex.evt.omniclaude.agent-match.v1"
    LATENCY_BREAKDOWN = "onex.evt.omniclaude.latency-breakdown.v1"

    # ==========================================================================
    # Routing feedback topics (OMN-1892)
    # ==========================================================================
    ROUTING_FEEDBACK = "onex.evt.omniclaude.routing-feedback.v1"
    # TOMBSTONED (OMN-2622): folded into ROUTING_FEEDBACK via feedback_status field.
    # Producer removed; topic no longer provisioned.
    # ROUTING_FEEDBACK_SKIPPED = "onex.evt.omniclaude.routing-feedback-skipped.v1"
    #
    # TOMBSTONED (OMN-2622): deprecated — no named consumer, raw signals not
    # suitable for long-term storage. Producer removed; topic no longer provisioned.
    # ROUTING_OUTCOME_RAW = "onex.evt.omniclaude.routing-outcome-raw.v1"

    # ==========================================================================
    # Routing decision topics (PR-92)
    # ==========================================================================
    ROUTING_DECISION = "onex.evt.omniclaude.routing-decision.v1"
    # Cross-domain CMD topic: producer=omniclaude, domain=omniintelligence.
    # Internal control plane — not an observability topic. No contract topic_base
    # (schema supports one topic_base per contract); governed via topic_allowlist.yaml.
    # Lifecycle: internal_control (OMN-3294)
    ROUTING_DECISION_CMD = "onex.cmd.omniintelligence.routing-decision.v1"  # noqa: arch-topic-naming

    # ==========================================================================
    # GitHub PR status topics (OMN-3294)
    # Lifecycle: Integration (stable) — governed by node_github_pr_watcher_effect/contract.yaml
    # ==========================================================================
    GITHUB_PR_STATUS = "onex.evt.omniclaude.github-pr-status.v1"
    # DLQ / error topic for the PR watcher node
    PR_WATCHER_FAILED = "onex.evt.omniclaude.pr-watcher-failed.v1"

    # ==========================================================================
    # Epic status topics (OMN-3294)
    # Lifecycle: Integration (stable) — governed by node_agent_inbox_effect/contract.yaml
    # ==========================================================================
    EPIC_STATUS = "onex.evt.omniclaude.epic-status.v1"

    # ==========================================================================
    # Personality logging telemetry topics (OMN-3294)
    # Lifecycle: Telemetry (best-effort, may be sampled) — governed by
    #            node_personality_logging_effect/contract.yaml
    # Note: Telemetry topics may be sampled or dropped. No business logic may
    #       hard-depend on them.
    # ==========================================================================
    LOG_EVENT_EMITTED = "onex.evt.omniclaude.log-event-emitted.v1"
    LOG_EVENT_RENDERED = "onex.evt.omniclaude.log-event-rendered.v1"

    # ==========================================================================
    # LLM routing observability topics (OMN-2273)
    # ==========================================================================
    LLM_ROUTING_DECISION = "onex.evt.omniclaude.llm-routing-decision.v1"
    LLM_ROUTING_FALLBACK = "onex.evt.omniclaude.llm-routing-fallback.v1"

    # ==========================================================================
    # Notification topics (OMN-1831)
    # ==========================================================================
    NOTIFICATION_BLOCKED = "onex.evt.omniclaude.notification-blocked.v1"
    NOTIFICATION_COMPLETED = "onex.evt.omniclaude.notification-completed.v1"

    # ==========================================================================
    # Phase metrics topics (OMN-2027 - pipeline measurement)
    # ==========================================================================
    PHASE_METRICS = "onex.evt.omniclaude.phase-metrics.v1"

    # ==========================================================================
    # Manifest injection topics (agent loading observability)
    # ==========================================================================
    MANIFEST_INJECTION_STARTED = "onex.evt.omniclaude.manifest-injection-started.v1"
    MANIFEST_INJECTED = "onex.evt.omniclaude.manifest-injected.v1"
    MANIFEST_INJECTION_FAILED = "onex.evt.omniclaude.manifest-injection-failed.v1"

    # ==========================================================================
    # Agent status topics (OMN-1848 - agent lifecycle reporting)
    # ==========================================================================
    AGENT_STATUS = "onex.evt.omniclaude.agent-status.v1"

    # ==========================================================================
    # Transformation topics (agent transformation observability)
    # ==========================================================================
    TRANSFORMATION_STARTED = "onex.evt.omniclaude.transformation-started.v1"
    TRANSFORMATION_COMPLETED = "onex.evt.omniclaude.transformation-completed.v1"
    TRANSFORMATION_FAILED = "onex.evt.omniclaude.transformation-failed.v1"

    # ==========================================================================
    # Execution and observability topics (OMN-1552 migration)
    # ==========================================================================
    EXECUTION_LOGS = "onex.evt.omniclaude.agent-execution-logs.v1"
    AGENT_OBSERVABILITY = "onex.evt.omniclaude.agent-observability.v1"
    # DLQ for agent observability consumer (OMN-2959 — fixed from invalid f"{topic}-dlq")
    AGENT_OBSERVABILITY_DLQ = "onex.evt.omniclaude.agent-observability-dlq.v1"

    # ==========================================================================
    # Pattern compliance wiring (OMN-2263 → OMN-2256)
    # ==========================================================================
    COMPLIANCE_EVALUATE = "onex.cmd.omniintelligence.compliance-evaluate.v1"
    COMPLIANCE_EVALUATED = "onex.evt.omniintelligence.compliance-evaluated.v1"

    # ==========================================================================
    # Static context edit detection topics (OMN-2237)
    # ==========================================================================
    STATIC_CONTEXT_EDIT_DETECTED = "onex.evt.omniclaude.static-context-edit-detected.v1"

    # ==========================================================================
    # Enrichment observability topics (OMN-2274)
    # ==========================================================================
    CONTEXT_ENRICHMENT = "onex.evt.omniclaude.context-enrichment.v1"  # OMN-2274

    # ==========================================================================
    # Intelligence output topics (omniintelligence producers)
    # ==========================================================================
    PATTERN_STORED = "onex.evt.omniintelligence.pattern-stored.v1"
    """Emitted by omniintelligence when a pattern is persisted to the store."""

    RUN_EVALUATED = "onex.evt.omniintelligence.run-evaluated.v1"
    """Emitted by omniintelligence after a session run evaluation completes."""

    # ==========================================================================
    # Delegation observability topics (OMN-2281)
    # ==========================================================================
    TASK_DELEGATED = "onex.evt.omniclaude.task-delegated.v1"

    # ==========================================================================
    # Shadow validation topics (OMN-2283)
    # ==========================================================================
    DELEGATION_SHADOW_COMPARISON = "onex.evt.omniclaude.delegation-shadow-comparison.v1"

    # ==========================================================================
    # Pattern enforcement observability topics (OMN-2442)
    # Consumed by omnidash /enforcement dashboard
    # ==========================================================================
    PATTERN_ENFORCEMENT = "onex.evt.omniclaude.pattern-enforcement.v1"

    # ==========================================================================
    # Intent-to-commit binding topics (OMN-2492)
    # ==========================================================================
    INTENT_COMMIT_BOUND = "onex.evt.omniclaude.intent-commit-bound.v1"

    # ==========================================================================
    # Decision record topics (OMN-2465)
    # Privacy split: evt carries summary only; cmd carries full payload
    # ==========================================================================
    # Observability topic — broad access, summary fields only (no rationale/snapshot)
    DECISION_RECORDED_EVT = "onex.evt.omniintelligence.decision-recorded.v1"
    # Restricted topic — full payload including agent_rationale and reproducibility_snapshot
    DECISION_RECORDED_CMD = "onex.cmd.omniintelligence.decision-recorded.v1"

    # ==========================================================================
    # Decision store event bus topics (OMN-2766)
    # ==========================================================================
    DECISION_RECORDED_EVT_OMNICLAUDE = "onex.evt.omniclaude.decision-recorded.v1"
    DECISION_STATUS_CHANGED_EVT = "onex.evt.omniclaude.decision-status-changed.v1"
    DECISION_CONFLICT_DETECTED_EVT = "onex.evt.omniclaude.decision-conflict-detected.v1"
    DECISION_CONFLICT_STATUS_CHANGED = (
        "onex.evt.omniclaude.decision-conflict-status-changed.v1"
    )

    # ==========================================================================
    # ChangeFrame emission topics (OMN-2651)
    # ==========================================================================
    CHANGE_FRAME_EMITTED = "onex.evt.omniclaude.change-frame.v1"

    # ==========================================================================
    # Agent trace topics (OMN-2412)
    # ==========================================================================
    AGENT_TRACE_FIX_TRANSITION = "onex.evt.omniclaude.fix-transition.v1"

    # ==========================================================================
    # Quirks Detector topics (OMN-2556)
    # ==========================================================================
    QUIRK_SIGNAL_DETECTED = "onex.evt.omniclaude.quirk-signal-detected.v1"
    """Raw QuirkSignal emitted by NodeQuirkSignalExtractorEffect after detection."""

    QUIRK_FINDING_PRODUCED = "onex.evt.omniclaude.quirk-finding-produced.v1"
    """QuirkFinding emitted by NodeQuirkClassifierCompute after threshold is met."""

    # ==========================================================================
    # Skill lifecycle topics (OMN-2773)
    # Convention: event_type = dotted form, topic = dashed form.
    # ==========================================================================
    SKILL_STARTED = "onex.evt.omniclaude.skill-started.v1"
    """Emitted before skill dispatch; join key is run_id."""

    SKILL_COMPLETED = "onex.evt.omniclaude.skill-completed.v1"
    """Emitted after skill dispatch (success or failure); join key is run_id."""

    SKILL_INVOKED = "onex.evt.omniclaude.skill-invoked.v1"
    """Derived from skill.completed; consumed by omnidash skill_invocations projection (OMN-6800)."""

    # ==========================================================================
    # Friction observation topics (OMN-5747)
    # ==========================================================================
    FRICTION_OBSERVED = "onex.evt.omniclaude.friction-observed.v1"
    """Contract-driven friction classification output; partition key is session_id."""

    # ==========================================================================
    # Wave 2 pipeline observability topics (OMN-2922)
    # Consumed by omnidash Wave 2 projection nodes.
    # ==========================================================================
    EPIC_RUN_UPDATED = "onex.evt.omniclaude.epic-run-updated.v1"
    """State update for an in-flight epic run (one row per run_id in epic_run_lease)."""

    PR_WATCH_UPDATED = "onex.evt.omniclaude.pr-watch-updated.v1"
    """State update for an in-flight pr-watch session (one row per run_id in pr_watch_state)."""

    GATE_DECISION = "onex.evt.omniclaude.gate-decision.v1"
    """Append-only gate outcome (ACCEPTED, REJECTED, TIMEOUT) emitted by gate-aware skills."""

    BUDGET_CAP_HIT = "onex.evt.omniclaude.budget-cap-hit.v1"
    """Emitted when the token budget threshold is exceeded during context injection."""

    CIRCUIT_BREAKER_TRIPPED = "onex.evt.omniclaude.circuit-breaker-tripped.v1"
    """Emitted when the Kafka circuit breaker transitions to OPEN state."""

    # ==========================================================================
    # PR changeset and outcome topics (OMN-3138)
    # Delta Intelligence Phase 0 — emitted by pr-queue-pipeline for downstream
    # contract change tracking and merge gate decisions.
    # ==========================================================================
    PR_CHANGESET_CREATED = "onex.evt.omniclaude.pr-changeset-created.v1"
    """Emitted on PR open/update with detected contract changes."""

    MERGE_GATE_DECISION = "onex.evt.omniclaude.merge-gate-decision.v1"
    """Emitted with Tier A gate check results for contract changes."""

    PR_OUTCOME = "onex.evt.omniclaude.pr-outcome.v1"
    """Emitted after merge or revert detected for a tracked PR."""

    # ==========================================================================
    # PR validation rollup topics (OMN-3930 - MEI pipeline measurement)
    # ==========================================================================
    PR_VALIDATION_ROLLUP = "onex.evt.omniclaude.pr-validation-rollup.v1"
    """Emitted at pipeline completion with aggregated validation tax metrics and VTS."""

    # ==========================================================================
    # Correlation trace topics (OMN-5047)
    # Consumed by omnidash /trace page via correlation_trace_spans table.
    # ==========================================================================
    CORRELATION_TRACE = "onex.evt.omniclaude.correlation-trace.v1"
    """Trace span event emitted during active sessions for omnidash /trace page."""

    # ==========================================================================
    # DoD (Definition of Done) telemetry topics (OMN-5197)
    # Consumed by omnidash /dod dashboard via dod_verify_runs and
    # dod_guard_events tables.
    # ==========================================================================
    DOD_VERIFY_COMPLETED = "onex.evt.omniclaude.dod-verify-completed.v1"
    """Emitted after every DoD evidence verification run."""

    DOD_GUARD_FIRED = "onex.evt.omniclaude.dod-guard-fired.v1"
    """Emitted on every DoD guard interception (pre-tool-use hook)."""

    DOD_SWEEP_COMPLETED = "onex.evt.omniclaude.dod-sweep-completed.v1"
    """Emitted after a batch DoD compliance sweep completes."""

    # ==========================================================================
    # Evidence dual-write topics (OMN-7030)
    # Emitted by EvidenceWriter on every disk evidence write (fail-open).
    # ==========================================================================
    EVIDENCE_WRITTEN = "onex.evt.omniclaude.evidence-written.v1"
    """Emitted after evidence is written to disk (self-check or verifier)."""

    # ==========================================================================
    # Context integrity audit topics (OMN-5230)
    # Emitted by audit hooks for dispatch validation, scope enforcement,
    # budget tracking, return path control, and compression lifecycle.
    # ==========================================================================
    AUDIT_DISPATCH_VALIDATED = "onex.evt.omniclaude.audit-dispatch-validated.v1"
    """Emitted when a task dispatch is validated against its contract."""

    AUDIT_SCOPE_VIOLATION = "onex.evt.omniclaude.audit-scope-violation.v1"
    """Emitted when a scope boundary violation is detected during execution."""

    AUDIT_CONTEXT_BUDGET_EXCEEDED = (
        "onex.evt.omniclaude.audit-context-budget-exceeded.v1"
    )
    """Emitted when context budget usage is tracked or exceeded."""

    AUDIT_RETURN_BOUNDED = "onex.evt.omniclaude.audit-return-bounded.v1"
    """Emitted when return path size is evaluated against constraints."""

    AUDIT_COMPRESSION_TRIGGERED = "onex.evt.omniclaude.audit-compression-triggered.v1"
    """Emitted when context compression is triggered by budget or time limits."""

    AUDIT_RUN_REQUESTED = "onex.cmd.omniclaude.audit-run-requested.v1"
    """Command requesting an on-demand audit run for a session or task tree."""

    AUDIT_RUN_COMPLETED = "onex.evt.omniclaude.audit-run-completed.v1"
    """Emitted when an on-demand audit run completes with summary results."""

    # ==========================================================================
    # Validator catch topics (OMN-5549)
    # Emitted when a validator blocks or catches an issue during a session.
    # Consumed by the savings estimation pipeline for severity-weighted attribution.
    # ==========================================================================
    VALIDATOR_CATCH = "onex.evt.omniclaude.validator-catch.v1"
    """Emitted when a validator (poly-enforcer, bash-guard, pre-commit) catches an issue."""

    # ==========================================================================
    # Plan review topics (OMN-6128)
    # ==========================================================================
    PLAN_REVIEW_COMPLETED = "onex.evt.omniclaude.plan-review-completed.v1"
    """Emitted after hostile-reviewer convergence loop completes."""

    # ==========================================================================
    # Multi-model hostile reviewer topics (OMN-6188)
    # Emitted by aggregate_reviews.py on review completion or failure.
    # ==========================================================================
    HOSTILE_REVIEWER_COMPLETED = "onex.evt.omniclaude.hostile-reviewer-completed.v1"
    """Emitted when multi-model hostile review completes with aggregated findings."""

    HOSTILE_REVIEWER_FAILED = "onex.evt.omniclaude.hostile-reviewer-failed.v1"
    """Emitted when multi-model hostile review fails (no models produced results)."""

    # ==========================================================================
    # QPM (Queue Priority Manager) topics (OMN-6242)
    # ==========================================================================
    QPM_RUN = "onex.cmd.omniclaude.qpm-run.v1"
    """Command to trigger a QPM run (classify + score + decide + promote)."""

    QPM_CLASSIFIED = "onex.evt.omniclaude.qpm-classified.v1"
    """Emitted after QPM classification and scoring completes for all queried repos."""

    QPM_PROMOTION_DECIDED = "onex.evt.omniclaude.qpm-promotion-decided.v1"
    """Emitted after QPM promotion decision is executed or held for each PR."""

    # ==========================================================================
    # Agent chat broadcast topics (OMN-3972)
    # ==========================================================================
    AGENT_CHAT_BROADCAST = "onex.evt.omniclaude.agent-chat-broadcast.v1"
    """Broadcast chat message for multi-terminal agent coordination."""

    # ==========================================================================
    # Sprint auto-pull topics (OMN-6870)
    # Emitted by refill-sprint skill when tech debt tickets are pulled
    # from Future into Active Sprint.
    # ==========================================================================
    SPRINT_AUTO_PULL_COMPLETED = "onex.evt.omniclaude.sprint-auto-pull-completed.v1"
    """Emitted after refill-sprint completes a pull cycle."""

    TECH_DEBT_QUEUE_EMPTY = "onex.evt.omniclaude.tech-debt-queue-empty.v1"
    """Emitted when no eligible tech debt tickets remain in Future."""

    # ==========================================================================
    # Session coordination topics (OMN-6857)
    # Multi-session awareness signals for concurrent session coordination.
    # Consumed by session registry projector and graph projector.
    # ==========================================================================
    SESSION_COORDINATION_SIGNAL = "onex.evt.omniclaude.session-coordination-signal.v1"
    """Coordination signal emitted between sessions (PR merged, conflict detected, etc.)."""

    SESSION_STATUS_CHANGED = "onex.evt.omniclaude.session-status-changed.v1"
    """Session status change event for coordination projectors."""

    # ==========================================================================
    # Delegation pipeline command topics (OMN-7040)
    # Thin /delegate skill publishes to this topic; consumed by
    # node_delegation_orchestrator on the omnibase_infra runtime.
    # ==========================================================================
    DELEGATION_REQUEST = "onex.cmd.omnibase-infra.delegation-request.v1"
    """Command to request task delegation through the node-based pipeline.

    Aligned with the node_delegation_orchestrator contract in omnibase_infra.
    The runtime subscribes to this topic via EventBusSubcontractWiring.
    """

    # ==========================================================================
    # Team lifecycle topics (OMN-7026)
    # Unified event schema for all dispatch surfaces (team_worker,
    # headless_claude, local_llm). Consumed by omnidash team timeline.
    # ==========================================================================
    TEAM_TASK_ASSIGNED = "onex.evt.omniclaude.team-task-assigned.v1"
    """Emitted when a task is assigned to an agent on any dispatch surface."""

    TEAM_TASK_PROGRESS = "onex.evt.omniclaude.team-task-progress.v1"
    """Emitted at phase transitions during task execution."""

    TEAM_EVIDENCE_WRITTEN = "onex.evt.omniclaude.team-evidence-written.v1"
    """Emitted when an evidence artifact is persisted to disk."""

    TEAM_TASK_COMPLETED = "onex.evt.omniclaude.team-task-completed.v1"
    """Emitted when a task reaches a terminal state with a verification verdict."""

    # ==========================================================================
    # Delegation pipeline topics (OMN-7103)
    # Node-based delegation orchestrator command/event bus topics.
    # ==========================================================================
    DELEGATE_TASK = "onex.cmd.omniclaude.delegate-task.v1"
    """Command to request delegation of a task to a local LLM endpoint."""

    DELEGATION_COMPLETED = "onex.evt.omniclaude.delegation-completed.v1"
    """Emitted when a delegation pipeline run completes successfully."""

    DELEGATION_FAILED = "onex.evt.omniclaude.delegation-failed.v1"
    """Emitted when a delegation pipeline run fails at any stage."""

    # ==========================================================================
    # Hook health observability topics (OMN-7157)
    # ==========================================================================
    HOOK_HEALTH_ERROR = "onex.evt.omniclaude.hook-health-error.v1"
    """Structured hook error event for health observability dashboard."""

    # ==========================================================================
    # OmniClaw channel messaging topics (OMN-7185)
    # Inbound normalized messages from any channel adapter, outbound replies,
    # and processing observability.
    # ==========================================================================
    CHANNEL_MESSAGE_RECEIVED = "onex.cmd.omniclaw.channel-message-received.v1"
    """Inbound normalized message from any channel adapter. Payload: ModelChannelEnvelope."""

    CHANNEL_REPLY_REQUESTED = "onex.evt.omniclaw.channel-reply-requested.v1"
    """Outbound response to be dispatched to the originating channel adapter."""

    CHANNEL_MESSAGE_PROCESSED = "onex.evt.omniclaw.channel-message-processed.v1"
    """Observability event emitted after orchestrator processes a channel message."""

    # ==========================================================================
    # OmniClaw channel-specific outbound topics (OMN-7187)
    # Fan-out targets for the reply dispatcher. One per supported channel.
    # ==========================================================================
    CHANNEL_DISCORD_OUTBOUND = "onex.cmd.omniclaw.discord-outbound.v1"
    """Reply routed to Discord adapter."""

    CHANNEL_SLACK_OUTBOUND = "onex.cmd.omniclaw.slack-outbound.v1"
    """Reply routed to Slack adapter."""

    CHANNEL_TELEGRAM_OUTBOUND = "onex.cmd.omniclaw.telegram-outbound.v1"
    """Reply routed to Telegram adapter."""

    CHANNEL_EMAIL_OUTBOUND = "onex.cmd.omniclaw.email-outbound.v1"
    """Reply routed to Email adapter."""

    CHANNEL_SMS_OUTBOUND = "onex.cmd.omniclaw.sms-outbound.v1"
    """Reply routed to SMS adapter."""

    # ==========================================================================
    # Contract drift detection topics (OMN-8013)
    # Produced by onex_change_control governance_emitter when drift is detected.
    # Subscribed by omnidash contract-drift-routes for projection.
    # ==========================================================================
    CONTRACT_DRIFT_DETECTED = "onex.evt.onex-change-control.contract-drift-detected.v1"
    """Emitted by onex_change_control when contract drift is detected during check-drift."""

    # ==========================================================================
    # Build-loop lifecycle topics (OMN-7400)
    # Emitted by the omnibase_infra build-loop orchestrator on completion.
    # Subscribed by node_friction_observer_compute for friction analysis.
    # ==========================================================================
    BUILD_LOOP_BUILD_COMPLETED = "onex.evt.omnibase-infra.build-loop-build-completed.v1"
    """Emitted by the build-loop orchestrator after a successful build cycle."""

    BUILD_LOOP_FAILED = "onex.evt.omnibase-infra.build-loop-failed.v1"
    """Emitted by the build-loop orchestrator when a build cycle fails."""

    # ==========================================================================
    # omniweb content authoring topics (OMN-9659)
    # Lifecycle: Integration — consumed by node_content_projection (omnimarket)
    # ==========================================================================
    CONTENT_UPDATED = "onex.evt.omniweb.content-updated.v1"
    """Emitted when landing page YAML content is authored and committed."""


def _validate_topic_segment(segment: str, name: str) -> str:
    """Validate a single topic segment (prefix or base segment).

    Args:
        segment: The segment to validate.
        name: Name of the parameter for error messages.

    Returns:
        The stripped segment.

    Raises:
        ModelOnexError: If segment is None, not a string, or empty/whitespace-only.

    Example:
        >>> _validate_topic_segment("dev", "prefix")
        'dev'

        >>> _validate_topic_segment("  staging  ", "prefix")
        'staging'

        >>> _validate_topic_segment("", "prefix")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        ModelOnexError: ...
    """
    if segment is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"{name} must not be None",
        )

    if not isinstance(segment, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"{name} must be a string, got {type(segment).__name__}",
        )

    stripped = segment.strip()
    if not stripped:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"{name} must be a non-empty string",
        )

    return stripped


def _validate_topic_name(topic: str) -> None:
    """Validate that a topic name is well-formed.

    A well-formed topic name consists of alphanumeric segments (with underscores
    and hyphens allowed) separated by single dots. No leading/trailing dots,
    no consecutive dots, and no special characters except dots between segments.

    Args:
        topic: The full topic name to validate.

    Returns:
        None. This function validates in-place and raises on error.

    Raises:
        ModelOnexError: If topic name is malformed (leading/trailing dots,
            consecutive dots, empty segments, or invalid characters).

    Example:
        >>> _validate_topic_name("onex.evt.omniclaude.session-started.v1")  # Valid, no error

        >>> _validate_topic_name(".invalid")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        ModelOnexError: ...

        >>> _validate_topic_name("also..invalid")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        ModelOnexError: ...
    """
    # Check for leading/trailing dots
    if topic.startswith("."):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"Topic name must not start with a dot: {topic!r}",
        )
    if topic.endswith("."):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"Topic name must not end with a dot: {topic!r}",
        )

    # Check for consecutive dots
    if ".." in topic:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"Topic name must not contain consecutive dots: {topic!r}",
        )

    # Validate each segment
    segments = topic.split(".")
    for segment in segments:
        if not segment:
            # Empty segment (shouldn't happen after above checks, but be defensive)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                message=f"Topic name contains empty segment: {topic!r}",
            )
        if not _TOPIC_SEGMENT_PATTERN.match(segment):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                message=f"Topic segment contains invalid characters: {segment!r} in {topic!r}",
            )


def build_topic(base: str) -> str:
    """Return the canonical topic name after validation.

    Since OMN-5212, the ``prefix`` parameter has been removed. All topics use
    canonical ONEX names with no environment prefix.

    Args:
        base: Canonical topic name from ``TopicBase``.

    Returns:
        The validated canonical topic name.

    Raises:
        ModelOnexError: If *base* is empty, None, whitespace-only, or malformed.

    Examples:
        >>> build_topic(TopicBase.SESSION_STARTED)
        'onex.evt.omniclaude.session-started.v1'
    """
    base = _validate_topic_segment(base, "base")
    _validate_topic_name(base)
    if not _CANONICAL_TOPIC_PATTERN.match(base):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=(
                f"Topic {base!r} does not match canonical ONEX format "
                "onex.(cmd|evt|dlq|i*).<service>.<event>.v<N>"
            ),
        )
    return base


# Base prefix for per-agent directed inbox topics (OMN-8634).
# Not a TopicBase member — not a full canonical topic name.
# Full topic: AGENT_INBOX_DIRECTED_BASE + "." + agent_id + ".v1"
AGENT_INBOX_DIRECTED_BASE: str = "onex.evt.omniclaude.agent-inbox"  # noqa: arch-topic-naming


def build_agent_inbox_directed_topic(agent_id: str) -> str:
    """Return the directed agent inbox topic for a specific agent.

    Directed inbox topics are per-agent: ``onex.evt.omniclaude.agent-inbox.{agent_id}.v1``.

    Args:
        agent_id: The agent identifier to embed in the topic name.

    Returns:
        Full canonical topic name for the given agent.

    Examples:
        >>> build_agent_inbox_directed_topic("agent-001")
        'onex.evt.omniclaude.agent-inbox.agent-001.v1'
    """
    agent_id = _validate_topic_segment(agent_id, "agent_id")
    if not _TOPIC_SEGMENT_PATTERN.fullmatch(agent_id):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=(
                f"agent_id must be a single valid topic segment "
                f"(alphanumeric, hyphens, underscores only), got: {agent_id!r}"
            ),
        )
    return f"{AGENT_INBOX_DIRECTED_BASE}.{agent_id}.v1"
