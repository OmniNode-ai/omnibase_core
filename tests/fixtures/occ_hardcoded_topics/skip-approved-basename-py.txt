# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical topic constants for omnimarket event publication."""

from __future__ import annotations

TOPIC_LLM_CALL_COMPLETED = "onex.evt.omniintelligence.llm-call-completed.v1"  # onex-topic-allow: canonical topic registry, source of truth for all omnimarket topic constants

NODE_GENERATION_REQUESTED_TOPIC_V1 = "onex.cmd.omnimarket.node-generation-requested.v1"  # onex-topic-allow: canonical topic registry; declared in node_generation_consumer contract.yaml subscribe_topics

# OMN-13468: node-generation terminal topics. The failure terminal was missing
# from the topic registry and the projection contract, making failed runs
# invisible at GET /projection/onex.evt.omnimarket.node-generation-failed.v1
# (404 unknown_topic). Both terminals share the same payload shape
# (ModelGenerationBenchmark) and write to the generation_events table; only
# contract_passed differs (True for completed, False for failed).
NODE_GENERATION_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.node-generation-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_generation_consumer contract.yaml publish_topics + node_projection_delegation subscribe_topics (OMN-13468)
NODE_GENERATION_FAILED_TOPIC_V1 = "onex.evt.omnimarket.node-generation-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_generation_consumer contract.yaml publish_topics + node_projection_delegation subscribe_topics (OMN-13468)

# OMN-16316: BYOK inference-credential intake. The gateway's value->ref
# exchange (POST /v1/tenants/me/inference-credentials) publishes ONLY these
# two events -- never the secret value -- for node_projection_tenant_credentials
# to consume into the tenant_inference_credentials ref catalog.
CREDENTIAL_REGISTERED_TOPIC_V1 = "onex.evt.omnimarket.credential-registered.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_tenant_credentials contract.yaml subscribe_topics (OMN-16316)
CREDENTIAL_REVOKED_TOPIC_V1 = "onex.evt.omnimarket.credential-revoked.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_tenant_credentials contract.yaml subscribe_topics (OMN-16316)

# OMN-13629 (WS-F Phase 1): the legacy compat task-delegated.v1 event is no
# longer published by node_delegation_orchestrator nor subscribed by the
# delegation/savings projections — the terminal collapsed to the single
# canonical delegation-{completed,failed}.v1 pair below. The constant is retained
# only as a registry reference for the in-process RuntimeLocal discriminator and
# legacy tests; it is no longer a live wired topic.
TASK_DELEGATED_TOPIC_V1 = "onex.evt.omniclaude.task-delegated.v1"  # onex-topic-allow: canonical topic registry; legacy compat topic, no live producer/consumer after OMN-13629

# Namespace prefix for all omniclaude event topics (OMN-13694). Used by
# node_bus_audit_compute to detect CONTRACT_TOPIC_UNREGISTERED violations
# scoped to the omniclaude namespace. Declared here so that any namespace
# rename surfaces as a compile-time import error rather than a silent audit
# regression. This is a prefix string, not a versioned topic identifier.
OMNICLAUDE_EVT_TOPIC_PREFIX = "onex.evt.omniclaude."  # onex-topic-allow: canonical namespace prefix; referenced by node_bus_audit_compute handler for omniclaude-scoped unregistered-topic detection (OMN-13694)

# OMN-13629: canonical single delegation terminal pair. Emitted by
# node_delegation_orchestrator _emit_terminal; consumed by
# node_projection_delegation + node_projection_savings.
DELEGATION_COMPLETED_TOPIC_V1 = "onex.evt.omnibase-infra.delegation-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegation_orchestrator contract.yaml publish_topics (OMN-13629)
DELEGATION_FAILED_TOPIC_V1 = "onex.evt.omnibase-infra.delegation-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegation_orchestrator contract.yaml publish_topics (OMN-13629)
DELEGATION_DISPOSITION_RECORDED_TOPIC_V1 = "onex.evt.omnimarket.delegation-disposition-recorded.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_delegation_disposition contract.yaml subscribe_topics (OMN-20242)
DELEGATION_ACCEPTANCE_JUDGED_TOPIC_V1 = "onex.evt.omnimarket.delegation-acceptance-judged.v1"  # onex-topic-allow: canonical topic registry; offline calibrated verdicts, producer and consumer contracts follow in J.2/J.5
DELEGATE_SKILL_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.delegate-skill-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegate_skill_orchestrator contract.yaml terminal events
DELEGATE_SKILL_FAILED_TOPIC_V1 = "onex.evt.omnimarket.delegate-skill-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegate_skill_orchestrator contract.yaml terminal events
DELEGATION_CALL_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.delegation-call-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_llm_delegation_projection contract.yaml subscribe_topics
DELEGATION_ESCALATION_TRIGGERED_TOPIC_V1 = "onex.evt.omnimarket.delegation-escalation-triggered.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegation_routing_feedback_reducer contract.yaml subscribe_topics
DELEGATION_ALL_TIERS_FAILED_TOPIC_V1 = "onex.evt.omnimarket.delegation-all-tiers-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegation_routing_feedback_reducer contract.yaml subscribe_topics
DELEGATION_PROJECTION_SNAPSHOT_TOPIC_V1 = "onex.evt.omnimarket.delegation-projection-snapshot.v1"  # onex-topic-allow: canonical topic registry; declared in node_llm_delegation_projection contract.yaml publish_topics
ROUTING_FEEDBACK_UPDATED_TOPIC_V1 = "onex.evt.omnimarket.routing-feedback-updated.v1"  # onex-topic-allow: canonical topic registry; declared in node_delegation_routing_feedback_reducer contract.yaml publish_topics

# GitHub PR merge event (OMN-13226). Published by the pr-merged-publisher GHA
# workflow on every repo merge; consumed by node_pr_merged_projection (T3,
# OMN-13227) which materialises the projection at
# GET /projection/onex.evt.github.pr-merged.v1 on the .201 lane (:3002).
PR_MERGED_TOPIC_V1 = "onex.evt.github.pr-merged.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_merged_projection contract.yaml subscribe_topics (OMN-13226/13227)

# Merge-flow state-transition telemetry (OMN-14648 / WS6). Emitted per PR state
# transition through the merge flow; consumed by node_merge_state_projection,
# which materializes the merge_state_transitions projection so the merge-flow
# metrics (per-state duration, evidence-volume ratio baseline 1.67 -> target
# <=1.1, same-head reruns by reason) can be measured from the event log.
# REPORT-ONLY: no enforcement wired off this topic in the WS6 first PR.
MERGE_STATE_TRANSITION_TOPIC_V1 = "onex.evt.omnimarket.merge-state-transition.v1"  # onex-topic-allow: canonical topic registry; declared in node_merge_state_projection contract.yaml subscribe_topics (OMN-14648)

# OCC Evidence-Source autobind command (OMN-13317 / F1). Thin-published by the
# call-occ-autobind GHA workflow on product-PR opened/synchronize; consumed by
# node_pr_lifecycle_fix_effect, which routes it to the OccCompanionEmitter under
# the receipt_evidence_source_autobind block reason. The effect generates a
# receipt stamped with the real PR head + number, opens/syncs the OCC binding
# PR, recomputes contract_sha256 across all matching receipts, and PATCHes
# Evidence-Source: OCC#<n> back onto the product PR so occ-preflight goes green
# with zero manual edits.
OCC_AUTOBIND_COMMAND_TOPIC_V1 = "onex.cmd.omnimarket.occ-autobind.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_lifecycle_fix_effect contract.yaml subscribe_topics (OMN-13317)

# Canonical RSD-3 write-EFFECT command (OMN-14941 born path). Thin-published by
# the call-occ-companion-effect GHA caller (via the omniclaude reusable) on
# product-PR opened/synchronize; consumed by node_occ_companion_effect, which
# runs the deterministic read -> compute -> write OCC-companion producer cycle
# (RSD-2 state read, RSD-1 pure compute, git/gh side effects) and stamps
# Evidence-Source: OCC#<n> back onto the product PR. Only THIS path mints
# occ:machine-minted + minted_by_node=true. The published command MUST set
# mode="mutate" explicitly — the model defaults to dry_run (fail-safe), so an
# omitted mode is a silent no-mint (the optional-input-silent-skip trap).
OCC_COMPANION_EFFECT_COMMAND_TOPIC_V1 = "onex.cmd.omnimarket.occ-companion-effect-requested.v1"  # onex-topic-allow: canonical topic registry; declared in node_occ_companion_effect contract.yaml subscribe_topics (OMN-14941)

# OMN-19827 (epic OMN-19822, PR landing workflow, wave-1 task T5): the typed
# companion outcome, ModelPrLandingCompanionOutcome in
# omnimarket.events.pr_landing_companion. Published since wave-2 task T10
# (OMN-19832) by node_pr_lifecycle_fix_effect.
PR_LANDING_COMPANION_OUTCOME_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-companion-outcome.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_lifecycle_fix_effect contract.yaml publish_topics (OMN-19832)

# Typed FSM watchdog topics (OMN-12959). Canonical terminal-state-invariant
# vocabulary: every workflow FSM reaches a declared terminal OR trips one of
# these typed watchdogs. Consumed via omnimarket.events.watchdog, which maps the
# EnumWatchdogEventType class 1:1 to one of these topics.
TOPIC_WORKFLOW_TIMEOUT = "onex.evt.omnimarket.workflow-timeout.v1"  # onex-topic-allow: canonical typed-watchdog topic registry (OMN-12959)
TOPIC_WORKFLOW_UNROUTABLE = "onex.evt.omnimarket.workflow-unroutable.v1"  # onex-topic-allow: canonical typed-watchdog topic registry (OMN-12959)
TOPIC_WORKFLOW_STALLED = "onex.evt.omnimarket.workflow-stalled.v1"  # onex-topic-allow: canonical typed-watchdog topic registry (OMN-12959)

# Renderer capability declaration command (OMN-13131 / W5). A renderer thin-publishes
# its capability surface heartbeat onto this command topic; the sole writer
# node_renderer_capability_projection (NodeReducer) folds each declaration into the
# heartbeat-backed Renderer Capability Registry projection. The materialized
# projection (read via /projection/{topic}) is the only read authority — there is
# no in-memory registry class. The topic is the canonical source of truth for every
# Python consumer in the node path; the node's contract.yaml declares it for runtime
# wiring, and handler/model code references THIS constant (never the literal) so the
# no-hardcoded-topics gate stays green (G-E).
RENDERER_CAPABILITY_DECLARED_TOPIC_V1 = "onex.cmd.ui.renderer-capability-declared.v1"  # onex-topic-allow: canonical topic registry; declared in node_renderer_capability_projection contract.yaml subscribe_topics (OMN-13131)

# Context-ROI score event consumed by node_projection_capsule_store (OMN-12842).
# node_context_roi_compute emits this terminal event carrying the per-capsule
# effectiveness numbers; the capsule-store reducer folds each scored event into
# the durable capsule_store projection. The reducer references THESE constants
# (never the literals) so the no-hardcoded-topics gate stays green; the node's
# contract.yaml declares them for runtime wiring.
CONTEXT_ROI_SCORE_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.context-roi-score-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_context_roi_compute contract.yaml publish_topics and node_projection_capsule_store subscribe_topics (OMN-12842)
CAPSULE_STORE_APPLIED_TOPIC_V1 = "onex.evt.omnimarket.capsule-store-applied.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_capsule_store contract.yaml publish_topics (OMN-12842)

# M5 live closed-loop feedback edge (OMN-12845). The runner emits a scored
# runtime ROI row onto context-roi-runtime-row-scored.v1; the feedback-edge
# reducer (node_capsule_effectiveness_feedback_reducer) enforces attribution
# honesty: a CONTROLLED_INTERVENTION row is republished as a
# context-roi-score-completed.v1 effectiveness claim (folded onto the M2 capsule
# store, which then re-ranks M3 selection); an OBSERVATIONAL row is republished
# ONLY as a capsule-effectiveness-hypothesis.v1 and is never written as a measured
# score. Handler/model code references THESE constants (never the literals) so the
# no-hardcoded-topics gate stays green; each node's contract.yaml declares them.
CONTEXT_ROI_RUNTIME_ROW_SCORED_TOPIC_V1 = "onex.evt.omnimarket.context-roi-runtime-row-scored.v1"  # onex-topic-allow: canonical topic registry; declared in node_capsule_effectiveness_feedback_reducer contract.yaml subscribe_topics (OMN-12845)
CAPSULE_EFFECTIVENESS_HYPOTHESIS_TOPIC_V1 = "onex.evt.omnimarket.capsule-effectiveness-hypothesis.v1"  # onex-topic-allow: canonical topic registry; declared in node_capsule_effectiveness_feedback_reducer contract.yaml publish_topics (OMN-12845)

# OMN-13655: canonical redeploy bus path. The CI pipeline (or a thin agent shim)
# emits a ModelRuntimeImageBuilt onto RUNTIME_IMAGE_BUILT_TOPIC_V1 once an image
# has been pushed to the registry; the redeploy orchestrator subscribes and routes
# the event through the prod-promotion gate (replacing the prior imperative deploy
# script path). REDEPLOY_START_CMD_TOPIC_V1 is the original trigger topic exposed
# here so handler/model code references the constant (never the literal) and the
# no-hardcoded-topics gate stays green.
RUNTIME_IMAGE_BUILT_TOPIC_V1 = "onex.evt.omnimarket.runtime-image-built.v1"  # onex-topic-allow: canonical topic registry; declared in node_redeploy_orchestrator contract.yaml subscribe_topics (OMN-13655)
REDEPLOY_START_CMD_TOPIC_V1 = "onex.cmd.omnimarket.redeploy-start.v1"  # onex-topic-allow: canonical topic registry; declared in node_redeploy_orchestrator contract.yaml subscribe_topics (OMN-13655)

# OMN-17810: the one pr-lifecycle topic node_pr_lifecycle_state_reducer can
# project into pr_lifecycle_ledger_entries. Its producer
# (node_pr_lifecycle_fix_effect's terminal event) emits a PR-scoped observation
# carrying repo, pr_number, block_reason, fix_applied, fix_action and
# completed_at. The reducer's model references THIS constant (never the
# literal) so the no-hardcoded-topics gate stays green; both nodes' contract.yaml
# declare it for runtime wiring.
PR_LIFECYCLE_FIX_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.pr-lifecycle-fix-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_lifecycle_fix_effect contract.yaml publish_topics and node_pr_lifecycle_state_reducer subscribe_topics (OMN-17810)

# PR landing workflow (plan: PR landing workflow, section 5.3; OMN-19824). The
# four events node_pr_landing_orchestrator publishes: one per transition (with a
# per-key seq, the landing projection's ordering authority), one when only an
# agent can move the PR, and one per terminal. Wave 1 freezes the names and the
# payload classes (node_pr_landing_orchestrator.event_topics); the orchestrator
# contract declares them in event_bus and published_events, in the same commit
# as the projection's subscriptions (OMN-19829 wave-3 compose), because the hard
# contract-topic-graph gate refuses a producer with no consumer.
PR_LANDING_TRANSITIONED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-transitioned.v1"  # onex-topic-allow: canonical topic registry; published by node_pr_landing_orchestrator (OMN-19829), consumed by node_projection_pr_landing (OMN-19833)
PR_LANDING_AGENT_NEEDED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-agent-needed.v1"  # onex-topic-allow: canonical topic registry; published by node_pr_landing_orchestrator (OMN-19829), consumed by node_projection_pr_landing (OMN-19833)
PR_LANDING_MERGED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-merged.v1"  # onex-topic-allow: canonical topic registry; published by node_pr_landing_orchestrator (OMN-19829), consumed by node_projection_pr_landing (OMN-19833)
PR_LANDING_CLOSED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-closed.v1"  # onex-topic-allow: canonical topic registry; published by node_pr_landing_orchestrator (OMN-19829), consumed by node_projection_pr_landing (OMN-19833)
# OMN-19826: the PR landing workflow's GitHub effect (node_pr_landing_github_effect).
# The orchestrator publishes the request and consumes both results.
PR_LANDING_GITHUB_REQUESTED_TOPIC_V1 = "onex.cmd.omnimarket.pr-landing-github-requested.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_landing_github_effect contract.yaml event_bus (OMN-19826, OMN-19829)
PR_LANDING_GITHUB_COMPLETED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-github-completed.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_landing_github_effect contract.yaml event_bus (OMN-19826, OMN-19829)
PR_LANDING_GITHUB_FAILED_TOPIC_V1 = "onex.evt.omnimarket.pr-landing-github-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_landing_github_effect contract.yaml event_bus (OMN-19826, OMN-19829)
# OMN-20636: the PR handoff workflow. A lane publishes the request command;
# node_pr_handoff_orchestrator decides on the PR watcher's observations, has
# node_pr_handoff_ledger_effect append the handoff rows, and ends each request
# in one handed-off or failed terminal.
PR_HANDOFF_REQUESTED_TOPIC_V1 = "onex.cmd.omnimarket.pr-handoff-requested.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_orchestrator contract.yaml subscribe_topics (OMN-20636)
PR_HANDOFF_ACCEPTED_TOPIC_V1 = "onex.evt.omnimarket.pr-handoff-accepted.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_orchestrator contract.yaml publish_topics (OMN-20636)
PR_HANDOFF_HANDED_OFF_TOPIC_V1 = "onex.evt.omnimarket.pr-handoff-handed-off.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_orchestrator contract.yaml publish_topics (OMN-20636)
PR_HANDOFF_FAILED_TOPIC_V1 = "onex.evt.omnimarket.pr-handoff-failed.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_orchestrator contract.yaml publish_topics (OMN-20636)
PR_HANDOFF_LEDGER_APPEND_REQUESTED_TOPIC_V1 = "onex.cmd.omnimarket.pr-handoff-ledger-append-requested.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_ledger_effect contract.yaml subscribe_topics (OMN-20636)
PR_HANDOFF_LEDGER_APPENDED_TOPIC_V1 = "onex.evt.omnimarket.pr-handoff-ledger-appended.v1"  # onex-topic-allow: canonical topic registry; declared in node_pr_handoff_ledger_effect contract.yaml publish_topics (OMN-20636)
PR_STATE_OBSERVED_TOPIC_V1 = "onex.evt.omnimarket.pr-state-observed.v1"  # onex-topic-allow: canonical topic registry; published by node_pr_state_emit_effect, consumed by node_projection_pr_state and node_pr_handoff_orchestrator (OMN-19999, OMN-20636)
CI_RUN_FAILED_TOPIC_V1 = "onex.evt.omnimarket.ci-run-failed.v1"  # onex-topic-allow: canonical topic registry; declared in lifecycle triage and orchestrator contracts
CI_RED_TRIAGE_DECIDED_TOPIC_V1 = "onex.evt.omnimarket.ci-red-triage-decided.v1"  # onex-topic-allow: canonical topic registry; declared in lifecycle orchestrator and reducer contracts
PR_LIFECYCLE_ORCHESTRATOR_START_TOPIC_V1 = "onex.cmd.omnimarket.pr-lifecycle-orchestrator-start.v1"  # onex-topic-allow: canonical topic registry; declared in lifecycle orchestrator contract

PROJECTION_ROUTING_FEEDBACK_APPLIED_TOPIC_V1 = "onex.evt.omnimarket.projection-routing-feedback-applied.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_routing_feedback contract.yaml terminal_event
PROJECTION_ROUTING_FEEDBACK_MALFORMED_DLQ_TOPIC_V1 = "onex.dlq.omnimarket.projection-routing-feedback-malformed.v1"  # onex-topic-allow: canonical topic registry; declared in node_projection_routing_feedback contract.yaml dlq_topics
