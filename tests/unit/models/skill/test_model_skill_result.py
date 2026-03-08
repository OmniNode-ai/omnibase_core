# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSkillResult base contract."""

from __future__ import annotations

import json
from datetime import UTC

import pytest

from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus
from omnibase_core.models.skill.model_skill_result import ModelSkillResult


@pytest.mark.unit
class TestModelSkillResultConstruction:
    """Basic construction and field defaults."""

    def test_minimal_construction(self) -> None:
        result = ModelSkillResult(
            skill_name="ci-watch",
            status=EnumSkillResultStatus.SUCCESS,
        )
        assert result.skill_name == "ci-watch"
        assert result.status == EnumSkillResultStatus.SUCCESS
        assert result.extra_status is None
        assert result.extra == {}
        assert result.run_id is None
        assert result.repo is None
        assert result.pr_number is None
        assert result.ticket_id is None

    def test_full_construction(self) -> None:
        result = ModelSkillResult(
            skill_name="auto-merge",
            status=EnumSkillResultStatus.SUCCESS,
            extra_status="merged",
            run_id="pipeline-1709856000-OMN-1234",
            repo="omniclaude",
            pr_number=574,
            ticket_id="OMN-1234",
            extra={"merge_commit": "abc123", "strategy": "squash"},
        )
        assert result.extra_status == "merged"
        assert result.extra["merge_commit"] == "abc123"
        assert result.pr_number == 574
        assert result.ticket_id == "OMN-1234"

    def test_created_at_auto_populated(self) -> None:
        result = ModelSkillResult(skill_name="x", status=EnumSkillResultStatus.SUCCESS)
        assert result.created_at is not None
        assert result.created_at.tzinfo == UTC

    def test_frozen(self) -> None:
        result = ModelSkillResult(
            skill_name="ci-watch",
            status=EnumSkillResultStatus.SUCCESS,
        )
        with pytest.raises(Exception):  # ValidationError for frozen
            result.status = EnumSkillResultStatus.FAILED  # type: ignore[misc]


@pytest.mark.unit
class TestModelSkillResultDelegation:
    """Property delegation to EnumSkillResultStatus."""

    def test_is_terminal_success(self) -> None:
        result = ModelSkillResult(skill_name="x", status=EnumSkillResultStatus.SUCCESS)
        assert result.is_terminal

    def test_is_terminal_pending(self) -> None:
        result = ModelSkillResult(skill_name="x", status=EnumSkillResultStatus.PENDING)
        assert not result.is_terminal

    def test_is_success_like_partial(self) -> None:
        result = ModelSkillResult(skill_name="x", status=EnumSkillResultStatus.PARTIAL)
        assert result.is_success_like

    def test_is_success_like_failed(self) -> None:
        result = ModelSkillResult(skill_name="x", status=EnumSkillResultStatus.FAILED)
        assert not result.is_success_like


@pytest.mark.unit
class TestModelSkillResultSerialization:
    """JSON roundtrip and serialization."""

    def test_json_roundtrip(self) -> None:
        result = ModelSkillResult(
            skill_name="ci-watch",
            status=EnumSkillResultStatus.SUCCESS,
            run_id="run-123",
            extra={"fix_cycles_used": 2},
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["skill_name"] == "ci-watch"
        assert parsed["status"] == "success"

        restored = ModelSkillResult.from_json(json_str)
        assert restored.skill_name == result.skill_name
        assert restored.status == result.status
        assert restored.extra["fix_cycles_used"] == 2

    def test_extra_status_preserved_through_roundtrip(self) -> None:
        """Review fix: extra_status must survive JSON roundtrip."""
        result = ModelSkillResult(
            skill_name="auto-merge",
            status=EnumSkillResultStatus.GATED,
            extra_status="held",
            extra={"merge_commit": "abc123"},
        )
        json_str = result.to_json()
        restored = ModelSkillResult.from_json(json_str)
        assert restored.extra_status == "held"
        assert restored.extra["merge_commit"] == "abc123"

    def test_status_enum_string_deserialization(self) -> None:
        """Enum values can be deserialized from plain strings."""
        json_str = json.dumps(
            {
                "skill_name": "test",
                "status": "failed",
            }
        )
        result = ModelSkillResult.from_json(json_str)
        assert result.status == EnumSkillResultStatus.FAILED


@pytest.mark.unit
class TestModelSkillResultValidation:
    """Field validation and normalization."""

    def test_skill_name_whitespace_stripped(self) -> None:
        """Review fix 1: strip whitespace on skill_name."""
        result = ModelSkillResult(
            skill_name="  ci-watch  ",
            status=EnumSkillResultStatus.SUCCESS,
        )
        assert result.skill_name == "ci-watch"

    def test_skill_name_empty_rejected(self) -> None:
        """Review fix 1: reject empty skill_name after strip."""
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="   ",
                status=EnumSkillResultStatus.SUCCESS,
            )

    def test_ticket_id_whitespace_stripped(self) -> None:
        """Review fix 1: strip whitespace on ticket_id."""
        result = ModelSkillResult(
            skill_name="x",
            status=EnumSkillResultStatus.SUCCESS,
            ticket_id="  OMN-1234  ",
        )
        assert result.ticket_id == "OMN-1234"

    def test_ticket_id_valid_pattern(self) -> None:
        """Review fix 2: ticket_id must match ^[A-Z]+-[0-9]+$."""
        result = ModelSkillResult(
            skill_name="x",
            status=EnumSkillResultStatus.SUCCESS,
            ticket_id="DASH-56",
        )
        assert result.ticket_id == "DASH-56"

    def test_ticket_id_invalid_rejected(self) -> None:
        """Review fix 2: reject invalid ticket_id patterns."""
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="x",
                status=EnumSkillResultStatus.SUCCESS,
                ticket_id="bad",
            )

    def test_ticket_id_lowercase_rejected(self) -> None:
        """ticket_id pattern requires uppercase prefix."""
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="x",
                status=EnumSkillResultStatus.SUCCESS,
                ticket_id="omn-1234",
            )

    def test_ticket_id_none_allowed(self) -> None:
        """ticket_id is optional."""
        result = ModelSkillResult(
            skill_name="x",
            status=EnumSkillResultStatus.SUCCESS,
            ticket_id=None,
        )
        assert result.ticket_id is None

    def test_pr_number_ge_1(self) -> None:
        """Review fix 3: pr_number must be >= 1."""
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="x",
                status=EnumSkillResultStatus.SUCCESS,
                pr_number=0,
            )

    def test_pr_number_negative_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="x",
                status=EnumSkillResultStatus.SUCCESS,
                pr_number=-1,
            )

    def test_pr_number_valid(self) -> None:
        result = ModelSkillResult(
            skill_name="x",
            status=EnumSkillResultStatus.SUCCESS,
            pr_number=1,
        )
        assert result.pr_number == 1

    def test_pr_number_none_allowed(self) -> None:
        result = ModelSkillResult(
            skill_name="x",
            status=EnumSkillResultStatus.SUCCESS,
            pr_number=None,
        )
        assert result.pr_number is None

    def test_extra_forbids_unknown_top_level_fields(self) -> None:
        """Model uses extra='forbid' -- unknown fields are rejected."""
        with pytest.raises(Exception):
            ModelSkillResult(
                skill_name="x",
                status=EnumSkillResultStatus.SUCCESS,
                unknown_field="oops",  # type: ignore[call-arg]
            )
