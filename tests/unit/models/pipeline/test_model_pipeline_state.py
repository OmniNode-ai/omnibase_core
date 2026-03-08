# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelPipelineState and EnumPipelinePhase."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_pipeline_phase import EnumPipelinePhase
from omnibase_core.models.pipeline.model_phase_record import ModelPhaseRecord
from omnibase_core.models.pipeline.model_pipeline_state import ModelPipelineState


@pytest.mark.unit
class TestEnumPipelinePhase:
    """Tests for the EnumPipelinePhase enumeration."""

    def test_canonical_values_exist(self) -> None:
        """All expected pipeline phases are defined."""
        assert EnumPipelinePhase.INTAKE.value == "intake"
        assert EnumPipelinePhase.RESEARCH.value == "research"
        assert EnumPipelinePhase.SPEC.value == "spec"
        assert EnumPipelinePhase.IMPLEMENT.value == "implement"
        assert EnumPipelinePhase.LOCAL_REVIEW.value == "local_review"
        assert EnumPipelinePhase.CI_WATCH.value == "ci_watch"
        assert EnumPipelinePhase.PR_WATCH.value == "pr_watch"
        assert EnumPipelinePhase.CONTRACT_COMPLIANCE.value == "contract_compliance"
        assert EnumPipelinePhase.AUTO_MERGE.value == "auto_merge"
        assert EnumPipelinePhase.DONE.value == "done"
        assert EnumPipelinePhase.FAILED.value == "failed"

    def test_is_terminal(self) -> None:
        """DONE and FAILED are terminal; others are not."""
        assert EnumPipelinePhase.DONE.is_terminal
        assert EnumPipelinePhase.FAILED.is_terminal
        assert not EnumPipelinePhase.INTAKE.is_terminal
        assert not EnumPipelinePhase.IMPLEMENT.is_terminal
        assert not EnumPipelinePhase.CI_WATCH.is_terminal
        assert not EnumPipelinePhase.AUTO_MERGE.is_terminal

    def test_str_returns_value(self) -> None:
        """str() returns the value, not 'EnumPipelinePhase.INTAKE'."""
        assert str(EnumPipelinePhase.INTAKE) == "intake"
        assert str(EnumPipelinePhase.FAILED) == "failed"

    def test_total_phase_count(self) -> None:
        """Exactly 11 phases defined (guard against silent additions)."""
        assert len(EnumPipelinePhase) == 11


@pytest.mark.unit
class TestModelPhaseRecord:
    """Tests for the ModelPhaseRecord model."""

    def test_construction(self) -> None:
        record = ModelPhaseRecord(
            phase=EnumPipelinePhase.LOCAL_REVIEW,
            completed_at=datetime.now(UTC),
        )
        assert record.phase == EnumPipelinePhase.LOCAL_REVIEW
        assert record.artifacts == {}

    def test_frozen(self) -> None:
        """Phase records are immutable."""
        record = ModelPhaseRecord(
            phase=EnumPipelinePhase.IMPLEMENT,
            completed_at=datetime.now(UTC),
        )
        with pytest.raises(Exception):  # ValidationError for frozen model
            record.phase = EnumPipelinePhase.CI_WATCH  # type: ignore[misc]

    def test_naive_datetime_gets_utc(self) -> None:
        """Naive datetimes are normalized to UTC."""
        naive_dt = datetime(2026, 3, 8, 12, 0, 0)
        record = ModelPhaseRecord(
            phase=EnumPipelinePhase.INTAKE,
            completed_at=naive_dt,
        )
        assert record.completed_at.tzinfo == UTC

    def test_artifacts(self) -> None:
        record = ModelPhaseRecord(
            phase=EnumPipelinePhase.IMPLEMENT,
            completed_at=datetime.now(UTC),
            artifacts={"pr_url": "https://github.com/OmniNode-ai/omnibase_core/pull/1"},
        )
        assert record.artifacts["pr_url"].startswith("https://")


@pytest.mark.unit
class TestModelPipelineState:
    """Tests for the ModelPipelineState model."""

    def test_construction(self) -> None:
        state = ModelPipelineState(
            ticket_id="OMN-3795",
            current_phase=EnumPipelinePhase.IMPLEMENT,
            branch_name="jonah/omn-3795-fix-retry",
            title="Fix event handler retry",
        )
        assert state.ticket_id == "OMN-3795"
        assert state.current_phase == EnumPipelinePhase.IMPLEMENT
        assert state.phase_history == []
        assert state.pr_url is None
        assert state.run_id is None

    def test_mutable_for_phase_transitions(self) -> None:
        """Pipeline state is mutable -- phases transition during execution."""
        state = ModelPipelineState(
            ticket_id="OMN-3795",
            current_phase=EnumPipelinePhase.INTAKE,
            branch_name="jonah/omn-3795-fix",
            title="Fix",
        )
        # Should not raise -- mutable model
        state.current_phase = EnumPipelinePhase.RESEARCH
        assert state.current_phase == EnumPipelinePhase.RESEARCH

    def test_phase_history(self) -> None:
        now = datetime.now(UTC)
        state = ModelPipelineState(
            ticket_id="OMN-3795",
            current_phase=EnumPipelinePhase.CI_WATCH,
            branch_name="jonah/omn-3795-fix",
            title="Fix retry",
            phase_history=[
                ModelPhaseRecord(
                    phase=EnumPipelinePhase.INTAKE,
                    completed_at=now,
                ),
                ModelPhaseRecord(
                    phase=EnumPipelinePhase.IMPLEMENT,
                    completed_at=now,
                ),
            ],
        )
        assert len(state.phase_history) == 2
        assert state.phase_history[0].phase == EnumPipelinePhase.INTAKE

    def test_yaml_roundtrip(self) -> None:
        state = ModelPipelineState(
            ticket_id="OMN-3795",
            current_phase=EnumPipelinePhase.CI_WATCH,
            branch_name="jonah/omn-3795-fix",
            title="Fix retry",
            phase_history=[
                ModelPhaseRecord(
                    phase=EnumPipelinePhase.IMPLEMENT,
                    completed_at=datetime.now(UTC),
                ),
            ],
        )
        yaml_str = state.to_yaml()
        assert "ticket_id: OMN-3795" in yaml_str
        assert "current_phase: ci_watch" in yaml_str
        restored = ModelPipelineState.from_yaml(yaml_str)
        assert restored.ticket_id == state.ticket_id
        assert restored.current_phase == state.current_phase
        assert len(restored.phase_history) == 1

    def test_optional_fields(self) -> None:
        state = ModelPipelineState(
            ticket_id="OMN-3800",
            current_phase=EnumPipelinePhase.PR_WATCH,
            branch_name="jonah/omn-3800-add-feature",
            title="Add feature",
            run_id="run-abc-123",
            pr_url="https://github.com/OmniNode-ai/omnibase_core/pull/600",
            pr_number=600,
            repo="omnibase_core",
        )
        assert state.run_id == "run-abc-123"
        assert state.pr_number == 600
        assert state.repo == "omnibase_core"

    def test_required_fields_validation(self) -> None:
        """Required fields must be non-empty."""
        with pytest.raises(Exception):
            ModelPipelineState(
                ticket_id="",  # empty
                current_phase=EnumPipelinePhase.INTAKE,
                branch_name="b",
                title="t",
            )
        with pytest.raises(Exception):
            ModelPipelineState(
                ticket_id="OMN-1",
                current_phase=EnumPipelinePhase.INTAKE,
                branch_name="",  # empty
                title="t",
            )

    def test_timestamps_default_to_utc(self) -> None:
        state = ModelPipelineState(
            ticket_id="OMN-1",
            current_phase=EnumPipelinePhase.INTAKE,
            branch_name="b",
            title="t",
        )
        assert state.created_at.tzinfo is not None
        assert state.updated_at.tzinfo is not None


@pytest.mark.unit
class TestModelPipelineStateLegacyFixtures:
    """Legacy fixture tests: parse known pipeline state YAML schemas.

    These fixtures represent realistic YAML from actual
    ``~/.claude/pipelines/`` output. Both newer (with ``phase_history[]``)
    and older (with ``pipeline_state_version``) schemas must parse
    successfully.
    """

    NEWER_SCHEMA_YAML = """\
ticket_id: OMN-3795
current_phase: ci_watch
branch_name: jonah/omn-3795-fix-event-retry
title: "Fix event handler retry logic"
phase_history:
  - phase: intake
    completed_at: "2026-03-07T10:00:00+00:00"
    artifacts: {}
  - phase: research
    completed_at: "2026-03-07T10:05:00+00:00"
    artifacts: {}
  - phase: implement
    completed_at: "2026-03-07T10:30:00+00:00"
    artifacts:
      commit_sha: "abc123def"  # pragma: allowlist secret
run_id: "pipeline-run-80ef845a"  # pragma: allowlist secret
pr_url: "https://github.com/OmniNode-ai/omnibase_infra/pull/22"
pr_number: 22
repo: omnibase_infra
created_at: "2026-03-07T09:55:00+00:00"
updated_at: "2026-03-07T10:30:00+00:00"
"""

    OLDER_SCHEMA_YAML = """\
ticket_id: OMN-3600
current_phase: implement
branch_name: jonah/omn-3600-add-consumer
title: "Add Kafka consumer for agent events"
pipeline_state_version: 1
retry_count: 2
last_error: "CI timeout on integration tests"
created_at: "2026-02-28T14:00:00+00:00"
updated_at: "2026-02-28T15:30:00+00:00"
"""

    def test_newer_schema_parses(self) -> None:
        """Newer schema with phase_history[] parses correctly."""
        state = ModelPipelineState.from_yaml(self.NEWER_SCHEMA_YAML)
        assert state.ticket_id == "OMN-3795"
        assert state.current_phase == EnumPipelinePhase.CI_WATCH
        assert state.branch_name == "jonah/omn-3795-fix-event-retry"
        assert state.title == "Fix event handler retry logic"
        assert len(state.phase_history) == 3
        assert state.phase_history[0].phase == EnumPipelinePhase.INTAKE
        assert (
            state.phase_history[2].artifacts["commit_sha"] == "abc123def"
        )  # pragma: allowlist secret
        assert state.run_id == "pipeline-run-80ef845a"  # pragma: allowlist secret
        assert state.pr_number == 22
        assert state.repo == "omnibase_infra"

    def test_older_schema_parses_with_extra_fields(self) -> None:
        """Older schema with legacy fields (pipeline_state_version, retry_count)
        parses successfully due to extra='allow'."""
        state = ModelPipelineState.from_yaml(self.OLDER_SCHEMA_YAML)
        assert state.ticket_id == "OMN-3600"
        assert state.current_phase == EnumPipelinePhase.IMPLEMENT
        assert state.branch_name == "jonah/omn-3600-add-consumer"
        assert state.title == "Add Kafka consumer for agent events"
        assert state.phase_history == []  # not present in older schema
        # Legacy fields accessible via model_extra
        assert state.model_extra is not None
        assert state.model_extra.get("pipeline_state_version") == 1
        assert state.model_extra.get("retry_count") == 2
        assert state.model_extra.get("last_error") == "CI timeout on integration tests"

    def test_newer_schema_yaml_roundtrip_preserves_key_fields(self) -> None:
        """Key fields survive YAML roundtrip."""
        state = ModelPipelineState.from_yaml(self.NEWER_SCHEMA_YAML)
        yaml_str = state.to_yaml()
        restored = ModelPipelineState.from_yaml(yaml_str)
        assert restored.ticket_id == "OMN-3795"
        assert restored.current_phase == EnumPipelinePhase.CI_WATCH
        assert restored.branch_name == "jonah/omn-3795-fix-event-retry"
        assert len(restored.phase_history) == 3

    def test_older_schema_yaml_roundtrip_preserves_key_fields(self) -> None:
        """Key fields survive YAML roundtrip even with legacy extra fields."""
        state = ModelPipelineState.from_yaml(self.OLDER_SCHEMA_YAML)
        yaml_str = state.to_yaml()
        restored = ModelPipelineState.from_yaml(yaml_str)
        assert restored.ticket_id == "OMN-3600"
        assert restored.current_phase == EnumPipelinePhase.IMPLEMENT
        assert restored.branch_name == "jonah/omn-3600-add-consumer"

    def test_failed_phase_in_state(self) -> None:
        """FAILED phase is a valid current_phase for unrecoverable failures."""
        yaml_data = """\
ticket_id: OMN-3900
current_phase: failed
branch_name: jonah/omn-3900-broken
title: "Broken pipeline"
phase_history:
  - phase: intake
    completed_at: "2026-03-08T10:00:00+00:00"
    artifacts: {}
"""
        state = ModelPipelineState.from_yaml(yaml_data)
        assert state.current_phase == EnumPipelinePhase.FAILED
        assert state.current_phase.is_terminal
