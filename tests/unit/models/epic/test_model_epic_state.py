# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.models.epic.model_epic_state import (
    ModelEpicState,
    ModelEpicTicketStatus,
    ModelEpicWave,
)


@pytest.mark.unit
class TestModelEpicTicketStatus:
    def test_construction_minimal(self) -> None:
        ts = ModelEpicTicketStatus(
            ticket_id="OMN-3801",
            status="pr_opened",
        )
        assert ts.ticket_id == "OMN-3801"
        assert ts.status == "pr_opened"
        assert ts.pr_url is None
        assert ts.pr_number is None
        assert ts.branch is None
        assert ts.error is None
        assert ts.failure_type is None

    def test_construction_full(self) -> None:
        ts = ModelEpicTicketStatus(
            ticket_id="OMN-3801",
            status="pr_opened",
            pr_url="https://github.com/OmniNode-ai/omniclaude/pull/574",
            pr_number=574,
            branch="jonah/omn-3801-feature",
            error=None,
            failure_type=None,
        )
        assert ts.pr_url == "https://github.com/OmniNode-ai/omniclaude/pull/574"
        assert ts.pr_number == 574
        assert ts.branch == "jonah/omn-3801-feature"

    def test_extra_fields_allowed(self) -> None:
        """Extra fields should be accepted for migration compatibility."""
        ts = ModelEpicTicketStatus(
            ticket_id="OMN-3801",
            status="merged",
            some_extra_field="value",
        )
        assert ts.ticket_id == "OMN-3801"

    def test_ticket_id_required(self) -> None:
        with pytest.raises(Exception):
            ModelEpicTicketStatus(status="pending")  # type: ignore[call-arg]

    def test_status_required(self) -> None:
        with pytest.raises(Exception):
            ModelEpicTicketStatus(ticket_id="OMN-3801")  # type: ignore[call-arg]

    def test_empty_ticket_id_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelEpicTicketStatus(ticket_id="", status="pending")

    def test_empty_status_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelEpicTicketStatus(ticket_id="OMN-3801", status="")


@pytest.mark.unit
class TestModelEpicWave:
    def test_construction_minimal(self) -> None:
        wave = ModelEpicWave(wave_number=1)
        assert wave.wave_number == 1
        assert wave.ticket_ids == []
        assert wave.status == "pending"

    def test_construction_with_tickets(self) -> None:
        wave = ModelEpicWave(
            wave_number=1,
            ticket_ids=["OMN-3801", "OMN-3802"],
            status="in_progress",
        )
        assert len(wave.ticket_ids) == 2
        assert wave.status == "in_progress"

    def test_wave_number_ge_1(self) -> None:
        with pytest.raises(Exception):
            ModelEpicWave(wave_number=0)

    def test_extra_fields_allowed(self) -> None:
        wave = ModelEpicWave(
            wave_number=2,
            status="done",
            custom_field="value",
        )
        assert wave.wave_number == 2


@pytest.mark.unit
class TestModelEpicState:
    def test_construction_minimal(self) -> None:
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="epic-run-123",
        )
        assert state.epic_id == "OMN-3800"
        assert state.run_id == "epic-run-123"
        assert state.status == "queued"
        assert state.waves == []
        assert state.ticket_statuses == {}
        assert state.failures == {}
        assert state.open_prs == {}

    def test_construction_with_status(self) -> None:
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="epic-run-123",
            status="monitoring",
        )
        assert state.status == "monitoring"

    def test_wave_with_tickets(self) -> None:
        wave = ModelEpicWave(
            wave_number=1,
            ticket_ids=["OMN-3801", "OMN-3802"],
            status="in_progress",
        )
        assert len(wave.ticket_ids) == 2

    def test_ticket_status(self) -> None:
        ts = ModelEpicTicketStatus(
            ticket_id="OMN-3801",
            status="pr_opened",
            pr_url="https://github.com/OmniNode-ai/omniclaude/pull/574",
        )
        assert ts.ticket_id == "OMN-3801"

    def test_yaml_roundtrip(self) -> None:
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="epic-run-123",
            status="done",
            waves=[
                ModelEpicWave(
                    wave_number=1,
                    ticket_ids=["OMN-3801"],
                    status="done",
                ),
            ],
            ticket_statuses={
                "OMN-3801": ModelEpicTicketStatus(
                    ticket_id="OMN-3801",
                    status="merged",
                ),
            },
        )
        yaml_str = state.to_yaml()
        restored = ModelEpicState.from_yaml(yaml_str)
        assert restored.epic_id == "OMN-3800"
        assert restored.run_id == "epic-run-123"
        assert restored.status == "done"
        assert len(restored.waves) == 1
        assert restored.waves[0].wave_number == 1
        assert restored.waves[0].ticket_ids == ["OMN-3801"]
        assert restored.waves[0].status == "done"
        assert "OMN-3801" in restored.ticket_statuses
        assert restored.ticket_statuses["OMN-3801"].status == "merged"

    def test_yaml_roundtrip_with_timestamps(self) -> None:
        ts = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="run-456",
            status="monitoring",
            created_at=ts,
            last_update_utc=ts,
        )
        yaml_str = state.to_yaml()
        restored = ModelEpicState.from_yaml(yaml_str)
        assert restored.epic_id == "OMN-3800"
        assert restored.created_at is not None
        assert restored.last_update_utc is not None

    def test_extra_fields_allowed(self) -> None:
        """Extra fields should be accepted for migration compatibility."""
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="run-789",
            status="done",
            title="Some Epic Title",
            repos=[{"name": "omnibase_core", "status": "done"}],
        )
        assert state.epic_id == "OMN-3800"

    def test_failures_tracking(self) -> None:
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="run-001",
            status="monitoring",
            failures={
                "OMN-3801": {"error": "CI failed", "attempt": 2},
            },
        )
        assert "OMN-3801" in state.failures

    def test_open_prs_tracking(self) -> None:
        state = ModelEpicState(
            epic_id="OMN-3800",
            run_id="run-001",
            status="monitoring",
            open_prs={
                "OMN-3801": "https://github.com/OmniNode-ai/omniclaude/pull/574",
            },
        )
        assert state.open_prs["OMN-3801"].endswith("/574")

    def test_empty_epic_id_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelEpicState(epic_id="", run_id="run-001")

    def test_empty_run_id_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelEpicState(epic_id="OMN-3800", run_id="")

    def test_all_observed_epic_statuses_accepted(self) -> None:
        """Verify all statuses from migration corpus are accepted as str."""
        observed_statuses = [
            "done",
            "monitoring",
            "prs_open",
            "wave0_complete",
            "phase3_complete",
            "in_review",
            "complete",
            "awaiting_merge",
            "queued",
            "running",
        ]
        for status in observed_statuses:
            state = ModelEpicState(
                epic_id="OMN-TEST",
                run_id="run-test",
                status=status,
            )
            assert state.status == status

    def test_all_observed_ticket_statuses_accepted(self) -> None:
        """Verify all ticket statuses from migration corpus are accepted as str."""
        observed_statuses = [
            "merged",
            "pr_open",
            "done",
            "pending",
            "pr_created",
            "completed",
            "in_review",
            "queued",
            "in-review",
            "blocked",
            "pr_open_ci_pending",
            "duplicate",
            "running",
            "resolved_manual",
            "manual",
            "auto-merge-pending",
            "auto_merge_pending",
            "skipped_manual",
            "ready_to_start",
            "pr_review_loop",
            "pr_pending_merge",
            "in_progress",
            "done_skipped",
            "dispatching",
            "deferred",
            "canceled",
            "auto_merge_pending",
            "ci_watch",
            "blocked_by_pr407",
            "blocked_by_omn2675",
            "blocked_by_OMN-3410",
            "auto_merge_held",
            "no-op",
            "merged_pending_approval",
            "pr_open_auto_merge_queued",
            "complete",
        ]
        for status in observed_statuses:
            ts = ModelEpicTicketStatus(
                ticket_id="OMN-TEST",
                status=status,
            )
            assert ts.status == status

    def test_all_observed_wave_statuses_accepted(self) -> None:
        """Verify all wave statuses from migration corpus are accepted as str."""
        observed_statuses = [
            "done",
            "pending",
            "merged",
            "running",
            "pr_created",
            "dispatching",
            "deferred",
            "completed",
            "blocked_design_decision",
        ]
        for status in observed_statuses:
            wave = ModelEpicWave(
                wave_number=1,
                status=status,
            )
            assert wave.status == status

    def test_alias_export(self) -> None:
        """EpicState alias should resolve to ModelEpicState."""
        from omnibase_core.models.epic.model_epic_state import EpicState

        assert EpicState is ModelEpicState

    def test_package_exports(self) -> None:
        """Package __init__ should re-export all public symbols."""
        from omnibase_core.models.epic import (
            EpicState,
            ModelEpicState,
            ModelEpicTicketStatus,
            ModelEpicWave,
        )

        assert EpicState is ModelEpicState
        assert ModelEpicWave is not None
        assert ModelEpicTicketStatus is not None
