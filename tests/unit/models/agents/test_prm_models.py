# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern
from omnibase_core.models.agents.model_prm_match import ModelPrmMatch
from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry


def test_enum_prm_pattern_members() -> None:
    assert {p.value for p in EnumPrmPattern} == {
        "repetition_loop",
        "ping_pong",
        "expansion_drift",
        "stuck_on_test",
        "context_thrash",
    }


def test_enum_prm_pattern_is_str_enum() -> None:
    assert EnumPrmPattern.REPETITION_LOOP.value == "repetition_loop"
    assert isinstance(EnumPrmPattern.REPETITION_LOOP, str)


def test_trajectory_entry_fields() -> None:
    entry = ModelTrajectoryEntry(
        step=1,
        agent="agent-a",
        action="edit",
        target="src/foo.py",
        result="ok",
    )
    assert entry.step == 1
    assert entry.agent == "agent-a"
    assert entry.action == "edit"
    assert entry.target == "src/foo.py"
    assert entry.result == "ok"


def test_trajectory_entry_is_frozen() -> None:
    entry = ModelTrajectoryEntry(
        step=1,
        agent="agent-a",
        action="edit",
        target="src/foo.py",
        result="ok",
    )
    with pytest.raises(Exception):
        entry.step = 99  # type: ignore[misc]  # NOTE(OMN-10367): frozen model enforcement


def test_prm_match_fields() -> None:
    match = ModelPrmMatch(
        pattern=EnumPrmPattern.REPETITION_LOOP,
        affected_agents=("agent-a",),
        affected_targets=("src/foo.py",),
        step_range=(1, 5),
        severity_level=2,
        dedup_key="repetition_loop:agent-a:src/foo.py:1-5",
    )
    assert match.pattern == EnumPrmPattern.REPETITION_LOOP
    assert match.affected_agents == ("agent-a",)
    assert match.affected_targets == ("src/foo.py",)
    assert match.step_range == (1, 5)
    assert match.severity_level == 2
    assert match.dedup_key == "repetition_loop:agent-a:src/foo.py:1-5"


def test_prm_match_is_frozen() -> None:
    match = ModelPrmMatch(
        pattern=EnumPrmPattern.PING_PONG,
        affected_agents=("agent-a", "agent-b"),
        affected_targets=("src/bar.py",),
        step_range=(2, 8),
        severity_level=1,
        dedup_key="ping_pong:agent-a,agent-b:src/bar.py:2-8",
    )
    with pytest.raises(Exception):
        match.severity_level = 3  # type: ignore[misc]  # NOTE(OMN-10367): frozen model enforcement


def test_prm_match_severity_must_be_1_2_or_3() -> None:
    with pytest.raises(Exception):
        ModelPrmMatch(
            pattern=EnumPrmPattern.EXPANSION_DRIFT,
            affected_agents=("agent-a",),
            affected_targets=("src/baz.py",),
            step_range=(0, 10),
            severity_level=4,  # type: ignore[arg-type]  # NOTE(OMN-10367): runtime severity validation
            dedup_key="expansion_drift:agent-a:src/baz.py:0-10",
        )
