# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the lane work types (OMN-26699)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_lane_work_blocked_reason import (
    EnumLaneWorkBlockedReason,
)
from omnibase_core.enums.enum_lane_work_event import EnumLaneWorkEvent
from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models import lane_work as pkg
from omnibase_core.models.lane_work import (
    ModelLaneHelpAnswer,
    ModelLaneHelpRequest,
    ModelLaneHelpTier,
    ModelLaneWorkAction,
    ModelLaneWorkChange,
    ModelLaneWorkEvent,
    ModelLaneWorkReceipt,
    ModelLaneWorkState,
    ModelLaneWorkStepReply,
    ModelLaneWorkTerminal,
    build_action_id,
    workflow_id_for,
)
from omnibase_core.models.lane_work.model_lane_work_action import MAX_WORKFLOW_ID_LENGTH

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 26, 15, 0, tzinfo=UTC)
HEAD = "a" * 40
WF = "omninode-ai-omnibase-core-2380-1"

CHANGE: dict[str, Any] = {
    "owner": "OmniNode-ai",
    "repo": "omnibase_core",
    "pr_number": 2380,
    "ticket": "OMN-26699",
}
ACTION: dict[str, Any] = {
    "actor": "agent",
    "action_id": f"{WF}-1-0",
    "name": "read_log",
}
TERMINAL_HANDED_OFF: dict[str, Any] = {
    "workflow_id": WF,
    "seq": 9,
    "kind": "handed_off",
    "change": CHANGE,
    "last_state": "handed_off",
    "proven_head": HEAD,
    "handoff_request_id": "req-1",
    "proof_receipt_id": "rcpt-1",
    "transitions_taken": 8,
    "started_at": NOW,
    "ended_at": NOW + timedelta(minutes=5),
}
TERMINAL_BLOCKED: dict[str, Any] = {
    "workflow_id": WF,
    "seq": 3,
    "kind": "blocked",
    "change": CHANGE,
    "last_state": "blocked",
    "reason": "not_claimed",
    "decision_needed": "none",
    "decision_owner": "orchestrator",
    "transitions_taken": 2,
    "started_at": NOW,
    "ended_at": NOW,
}
RECEIPT: dict[str, Any] = {
    "workflow_id": WF,
    "seq": 1,
    "receipt_id": "r-1",
    "kind": "transition",
    "input_id": "in-1",
    "event_kind": "start",
    "from_state": "queued",
    "to_state": "awaiting_worker",
    "action_ids": [f"{WF}-1-0"],
    "occurred_at": NOW,
}
TIER: dict[str, Any] = {
    "name": "tier-a",
    "backend_id": "harness:tier-harness-a:tier-model-a",
    "harness": "tier-harness-a",
    "model": "tier-model-a",
    "effort": "medium",
}

EXPECTED_EVENT_KINDS = [
    "start", "worker_started", "claim_confirmed", "claim_missing", "check_red",
    "check_pending", "check_green", "head_moved", "log_read", "cause_found",
    "cause_unknown", "fix_committed", "commit_refused", "pushed", "push_refused",
    "proof_passed", "proof_failed", "proof_posted", "proof_post_failed",
    "handoff_written", "handoff_failed", "deadline_passed", "help_cause_found",
    "help_retry", "help_stop", "help_failed", "unclassified",
    "repeat_bound_reached", "overlay_pr_needed", "status_requested",
]  # fmt: skip

# One valid payload per kind: the fields the kind owes, nothing else.
_OBS = {"head_sha": HEAD, "observed_at": NOW, "ci_read_at": NOW}
_ANS = {"action_id": f"{WF}-2-0"}
KIND_FIELDS: dict[str, dict[str, Any]] = {
    "start": {"workflow_id": None, "worker_tier": "sonnet"},
    "worker_started": {"lane_name": "lane-1"},
    "check_red": _OBS,
    "check_pending": _OBS,
    "check_green": _OBS,
    "head_moved": _OBS,
    "log_read": {"red_kind": "base_inherited"},
    "commit_refused": {"event_class": "hook"},
    "push_refused": {"event_class": "check_failed"},
    "proof_passed": {**_ANS, "head_sha": HEAD},
    "proof_failed": {**_ANS, "event_class": "tests"},
    "proof_posted": _ANS,
    "proof_post_failed": _ANS,
    "handoff_written": {**_ANS, "head_sha": HEAD, "request_id": "req-1"},
    "handoff_failed": {**_ANS, "head_sha": HEAD, "request_id": "req-1"},
    "deadline_passed": {"deadline_id": "worker", "deadline_attempt": 1},
    "help_cause_found": _ANS,
    "help_retry": {**_ANS, "help_origin": "pushing"},
    "help_stop": {**_ANS, "reason": "help_exhausted", "decision_needed": "none"},
    "help_failed": _ANS,
}


def make_event(kind: str, **overrides: Any) -> ModelLaneWorkEvent:
    fields: dict[str, Any] = {
        "kind": kind,
        "workflow_id": WF,
        "input_id": f"in-{kind}",
        "change": CHANGE,
        **KIND_FIELDS.get(kind, {}),
    }
    fields.update(overrides)
    return ModelLaneWorkEvent(**fields)


ALL_MODELS: list[tuple[type[BaseModel], dict[str, Any]]] = [
    (ModelLaneWorkChange, CHANGE),
    (ModelLaneWorkAction, ACTION),
    (ModelLaneWorkReceipt, RECEIPT),
    (ModelLaneWorkTerminal, TERMINAL_HANDED_OFF),
    (ModelLaneHelpTier, TIER),
    (
        ModelLaneWorkEvent,
        {"kind": "claim_missing", "workflow_id": WF, "input_id": "i", "change": CHANGE},
    ),
    (ModelLaneWorkState, {"workflow_id": WF, "change": CHANGE}),
    (
        ModelLaneWorkStepReply,
        {
            "workflow_id": WF,
            "state": "claimed",
            "seq": 2,
            "receipt_id": "r-2",
            "next_action": "agent_action",
            "action": ACTION,
        },
    ),
    (
        ModelLaneHelpRequest,
        {
            "workflow_id": WF,
            "state": "help_requested",
            "help_origin": "pushing",
            "question": "why?",
            "tier": TIER,
        },
    ),
    (ModelLaneHelpAnswer, {"kind": "help_cause_found", "cause": "stale base"}),
]


def test_event_enum_holds_the_30_kinds() -> None:
    assert len(EXPECTED_EVENT_KINDS) == 30
    assert [e.value for e in EnumLaneWorkEvent] == EXPECTED_EVENT_KINDS


def test_state_enum_holds_the_16_states() -> None:
    assert len(EnumLaneWorkState) == 16


@pytest.mark.parametrize("kind", EXPECTED_EVENT_KINDS)
def test_every_event_kind_builds(kind: str) -> None:
    assert make_event(kind).kind.value == kind


def test_unknown_event_kind_fails() -> None:
    with pytest.raises(ValidationError):
        make_event("teleported")


@pytest.mark.parametrize(
    ("kind", "missing"),
    [
        ("check_green", "ci_read_at"),
        ("log_read", "red_kind"),
        ("commit_refused", "event_class"),
        ("proof_passed", "action_id"),
        ("help_stop", "reason"),
        ("deadline_passed", "deadline_id"),
        ("worker_started", "lane_name"),
        ("status_requested", "workflow_id"),
    ],
)
def test_event_kind_owes_its_fields(kind: str, missing: str) -> None:
    with pytest.raises(ValidationError):
        make_event(kind, **{missing: None})


def test_event_class_outside_closed_list_fails() -> None:
    with pytest.raises(ValidationError):
        make_event("commit_refused", event_class="cosmic_ray")
    with pytest.raises(ValidationError):
        make_event("check_red", event_class="tests")


@pytest.mark.parametrize(
    "missing", ["proven_head", "handoff_request_id", "proof_receipt_id"]
)
def test_terminal_kind_fields_handed_off(missing: str) -> None:
    ModelLaneWorkTerminal(**TERMINAL_HANDED_OFF)
    with pytest.raises(ValidationError):
        ModelLaneWorkTerminal(**{**TERMINAL_HANDED_OFF, missing: None})


def test_terminal_kind_fields_blocked() -> None:
    ModelLaneWorkTerminal(**TERMINAL_BLOCKED)
    with pytest.raises(ValidationError):
        ModelLaneWorkTerminal(**{**TERMINAL_BLOCKED, "reason": None})
    with pytest.raises(ValidationError):
        ModelLaneWorkTerminal(**{**TERMINAL_BLOCKED, "decision_owner": None})
    with pytest.raises(ValidationError):
        ModelLaneWorkTerminal(**{**TERMINAL_BLOCKED, "proof_receipt_id": "x"})
    with pytest.raises(ValidationError):
        ModelLaneWorkTerminal(**{**TERMINAL_BLOCKED, "kind": "teleported"})


def test_blocked_reasons_are_the_contract_list() -> None:
    assert {r.value for r in EnumLaneWorkBlockedReason} == {
        "worker_never_started",
        "not_claimed",
        "worker_lost",
        "help_exhausted",
    }


def test_receipt_requires_seq_and_action_ids() -> None:
    ModelLaneWorkReceipt(**RECEIPT)
    for name in ("seq", "action_ids"):
        with pytest.raises(ValidationError):
            ModelLaneWorkReceipt(**{k: v for k, v in RECEIPT.items() if k != name})
    with pytest.raises(ValidationError):
        ModelLaneWorkReceipt(**{**RECEIPT, "seq": 0})


def test_refused_receipt_names_refusal_and_keeps_state() -> None:
    refused = {**RECEIPT, "kind": "refused", "to_state": "queued", "refusal": "no edge"}
    ModelLaneWorkReceipt(**refused)
    with pytest.raises(ValidationError):
        ModelLaneWorkReceipt(**{**refused, "refusal": None})


@pytest.mark.parametrize("bad", ["a:b-123456", "x" * 65, "short", "Upper-case-id"])
def test_action_id_must_be_plain(bad: str) -> None:
    with pytest.raises(ValidationError):
        ModelLaneWorkAction(actor="node", action_id=bad, name="n")


def test_action_actor_is_agent_or_node() -> None:
    with pytest.raises(ValidationError):
        ModelLaneWorkAction(actor="human", action_id=f"{WF}-1-0", name="n")


def test_longest_workflow_id_yields_plain_action_ids() -> None:
    longest = "w" * MAX_WORKFLOW_ID_LENGTH
    action_id = build_action_id(longest, 999_999, 99)
    assert len(action_id) == 64
    assert re.fullmatch(r"^[a-z0-9-]{8,64}$", action_id)
    ModelLaneWorkAction(actor="node", action_id=action_id, name="n")
    with pytest.raises(ValidationError):
        ModelLaneWorkEvent(
            kind="claim_missing", workflow_id=longest + "w", input_id="i", change=CHANGE
        )
    with pytest.raises(ModelOnexError):
        build_action_id(longest, 1_000_000, 0)


def test_workflow_id_for_is_plain_and_bounded() -> None:
    assert workflow_id_for("OmniNode-ai", "omnibase_core", 2380, 1) == (
        "omninode-ai-omnibase-core-2380-1"
    )
    with pytest.raises(ModelOnexError):
        workflow_id_for("o" * 40, "r" * 40, 1, 1)


@pytest.mark.parametrize(
    ("model", "fields"), ALL_MODELS, ids=lambda x: getattr(x, "__name__", "")
)
def test_models_are_frozen_and_forbid_extra(
    model: type[BaseModel], fields: dict[str, Any]
) -> None:
    instance = model(**fields)
    first = next(iter(model.model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, first, getattr(instance, first))
    with pytest.raises(ValidationError):
        model(**fields, unknown_field=1)


def test_step_reply_next_action_payloads() -> None:
    base: dict[str, Any] = {
        "workflow_id": WF,
        "state": "claimed",
        "seq": 2,
        "receipt_id": "r-2",
    }
    ModelLaneWorkStepReply(**base, next_action="wait", wait_deadline=NOW)
    ModelLaneWorkStepReply(
        **base,
        next_action="stop",
        terminal=ModelLaneWorkTerminal(**TERMINAL_BLOCKED),
    )
    with pytest.raises(ValidationError):
        ModelLaneWorkStepReply(**base, next_action="wait")
    with pytest.raises(ValidationError):
        ModelLaneWorkStepReply(
            **base, next_action="wait", wait_deadline=NOW, action=ACTION
        )
    with pytest.raises(ValidationError):
        ModelLaneWorkStepReply(
            **base, next_action="agent_action", action={**ACTION, "actor": "node"}
        )


def test_help_answer_kind_fields() -> None:
    ModelLaneHelpAnswer(kind="help_retry", help_origin="pushing")
    ModelLaneHelpAnswer(
        kind="help_stop", reason="help_exhausted", decision_needed="none"
    )
    for bad in (
        {"kind": "help_cause_found"},
        {"kind": "help_retry"},
        {"kind": "help_stop", "reason": "help_exhausted"},
        {"kind": "help_shrug"},
    ):
        with pytest.raises(ValidationError):
            ModelLaneHelpAnswer(**bad)


def test_help_request_keeps_at_most_three_receipts() -> None:
    receipt = ModelLaneWorkReceipt(**RECEIPT)
    fields = ALL_MODELS[8][1]
    ModelLaneHelpRequest(**fields, last_receipts=(receipt,) * 3)
    with pytest.raises(ValidationError):
        ModelLaneHelpRequest(**fields, last_receipts=(receipt,) * 4)


def test_lane_work_models_have_no_io_imports_or_topic_names() -> None:
    root = Path(str(pkg.__file__)).parent
    files = sorted(root.glob("*.py"))
    assert files, "lane_work package has no source files"
    pattern = re.compile(r"import (requests|httpx|subprocess)|onex\.(cmd|evt|intent)\.")
    offenders = [f.name for f in files if pattern.search(f.read_text())]
    assert offenders == []
