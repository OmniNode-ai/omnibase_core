# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


from typing import Literal

import pytest

import omnibase_core.agents.prm_escalation as prm_escalation
from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern
from omnibase_core.models.agents.model_prm_match import ModelPrmMatch

pytestmark = pytest.mark.unit


def _make_match(
    dedup_key: str,
    severity_level: Literal[1, 2, 3] = 1,
) -> ModelPrmMatch:
    return ModelPrmMatch(
        pattern=EnumPrmPattern.REPETITION_LOOP,
        affected_agents=("agent_a",),
        affected_targets=("target_x",),
        step_range=(0, 5),
        severity_level=severity_level,
        dedup_key=dedup_key,
    )


# AC1: First match → severity_level=1, advisory string
def test_first_match_returns_advisory() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-1")
    result = tracker.process(_make_match("key-a"))
    assert result.severity_level == 1
    assert isinstance(result.guidance, str)
    assert len(result.guidance) > 0
    assert result.telemetry is None


# AC2: Second match → severity_level=2, stronger guidance + telemetry record
def test_second_match_returns_stronger_guidance_and_telemetry() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-2")
    tracker.process(_make_match("key-b"))
    result = tracker.process(_make_match("key-b"))
    assert result.severity_level == 2
    assert isinstance(result.guidance, str)
    assert len(result.guidance) > len("advisory")
    assert result.telemetry is not None
    assert result.telemetry["dedup_key"] == "key-b"
    assert result.telemetry["severity_level"] == 2


# AC3: Third match → severity_level=3, hard-stop sentinel string
def test_third_match_returns_hard_stop() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-3")
    tracker.process(_make_match("key-c"))
    tracker.process(_make_match("key-c"))
    result = tracker.process(_make_match("key-c"))
    assert result.severity_level == 3
    assert "HARD_STOP" in result.guidance


# AC4: Distinct dedup_keys track independently
def test_distinct_keys_track_independently() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-4")
    r1 = tracker.process(_make_match("key-d"))
    r2 = tracker.process(_make_match("key-e"))
    assert r1.severity_level == 1
    assert r2.severity_level == 1  # independent counter


# AC5: State persists across calls within session (in-memory dict keyed by session_id)
def test_state_persists_across_calls() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-5")
    tracker.process(_make_match("key-f"))
    tracker.process(_make_match("key-f"))
    # Third call escalates — state accumulated from prior calls
    result = tracker.process(_make_match("key-f"))
    assert result.severity_level == 3


# Additional: fourth+ match caps at severity_level=3
def test_fourth_match_still_hard_stop() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-6")
    for _ in range(4):
        result = tracker.process(_make_match("key-g"))
    assert result.severity_level == 3


# Additional: tracker with same session_id shares state across instances
def test_shared_state_across_tracker_instances() -> None:
    tracker_a = prm_escalation.EscalationTracker(session_id="session-shared")
    tracker_b = prm_escalation.EscalationTracker(session_id="session-shared")
    tracker_a.process(_make_match("key-h"))
    tracker_b.process(_make_match("key-h"))
    result = tracker_b.process(_make_match("key-h"))
    assert result.severity_level == 3


def test_session_state_evicts_oldest_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prm_escalation.EscalationTracker.reset_all_sessions()
    monkeypatch.setattr(prm_escalation, "_MAX_SESSION_STATE_ENTRIES", 2)

    oldest = prm_escalation.EscalationTracker(session_id="session-oldest")
    oldest.process(_make_match("key-i"))
    prm_escalation.EscalationTracker(session_id="session-middle")

    prm_escalation.EscalationTracker(session_id="session-newest")

    result = oldest.process(_make_match("key-i"))

    assert result.severity_level == 1
    assert list(prm_escalation._SESSION_STATE) == [
        "session-newest",
        "session-oldest",
    ]


def test_session_state_can_be_reset() -> None:
    tracker = prm_escalation.EscalationTracker(session_id="session-reset")
    tracker.process(_make_match("key-k"))

    prm_escalation.EscalationTracker.reset_session("session-reset")
    result = tracker.process(_make_match("key-k"))

    assert result.severity_level == 1
