# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ``util_ticket_workflow_persistence`` (OMN-9142)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_ticket_workflow_phase import (
    EnumTicketWorkflowPhase,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.ticket.model_ticket_workflow_state import (
    ModelTicketWorkflowState,
    ModelWorkflowQuestion,
)
from omnibase_core.utils.util_ticket_workflow_persistence import (
    extract_workflow_state,
    persist_workflow_state_locally,
    update_description_with_workflow_state,
    workflow_state_to_yaml,
)


def _sample_state(phase: str = "spec") -> ModelTicketWorkflowState:
    return ModelTicketWorkflowState(
        ticket_id="OMN-1234",
        title="Test ticket",
        repo="omnimarket",
        phase=phase,  # type: ignore[arg-type]
        created_at="2026-04-18T00:00:00Z",
        updated_at="2026-04-18T00:00:00Z",
    )


@pytest.mark.unit
class TestWorkflowStateToYaml:
    def test_roundtrip_via_yaml(self) -> None:
        state = _sample_state()
        dumped = workflow_state_to_yaml(state)
        parsed = yaml.safe_load(dumped)
        assert parsed["ticket_id"] == "OMN-1234"
        assert parsed["phase"] == "spec"

    def test_phase_serializes_as_string(self) -> None:
        state = _sample_state(phase="implement")
        dumped = workflow_state_to_yaml(state)
        assert "phase: implement" in dumped


@pytest.mark.unit
class TestExtractWorkflowState:
    def test_returns_none_when_marker_missing(self) -> None:
        assert extract_workflow_state("Regular description.") is None

    def test_returns_none_when_fence_missing(self) -> None:
        desc = "Some text.\n\n## Contract\n\nNo yaml fence here."
        assert extract_workflow_state(desc) is None

    def test_returns_none_when_yaml_invalid(self) -> None:
        desc = "## Contract\n\n```yaml\n: : not valid : :\n```\n"
        assert extract_workflow_state(desc) is None

    def test_returns_none_when_yaml_is_scalar(self) -> None:
        desc = "## Contract\n\n```yaml\njust a string\n```\n"
        assert extract_workflow_state(desc) is None

    def test_returns_none_on_validation_failure(self) -> None:
        desc = "## Contract\n\n```yaml\nticket_id: 123\nphase: not_a_phase\n```\n"
        assert extract_workflow_state(desc) is None

    def test_parses_valid_embedded_state(self) -> None:
        state = _sample_state()
        desc = update_description_with_workflow_state("Original.", state)
        parsed = extract_workflow_state(desc)
        assert parsed is not None
        assert parsed.ticket_id == "OMN-1234"
        assert parsed.phase == EnumTicketWorkflowPhase.SPEC

    def test_uses_last_contract_marker(self) -> None:
        # Two ## Contract blocks — extractor takes the last (current) one.
        first = _sample_state(phase="intake")
        second = _sample_state(phase="review")
        desc = update_description_with_workflow_state("Start.", first)
        desc = (
            desc
            + "\n\n## Contract\n\n```yaml\n"
            + workflow_state_to_yaml(second)
            + "```\n"
        )
        parsed = extract_workflow_state(desc)
        assert parsed is not None
        assert parsed.phase == EnumTicketWorkflowPhase.REVIEW


@pytest.mark.unit
class TestUpdateDescriptionWithWorkflowState:
    def test_appends_when_no_existing_contract(self) -> None:
        state = _sample_state()
        result = update_description_with_workflow_state("Plain body.", state)
        assert "Plain body." in result
        assert "## Contract" in result
        assert "```yaml" in result
        assert "ticket_id: OMN-1234" in result

    def test_replaces_when_contract_exists(self) -> None:
        state_a = _sample_state(phase="intake")
        desc = update_description_with_workflow_state("Body.", state_a)
        state_b = state_a.model_copy(update={"title": "Updated title"})
        desc2 = update_description_with_workflow_state(desc, state_b)
        assert desc2.count("## Contract") == 1
        assert "Updated title" in desc2

    def test_preserves_pre_existing_body(self) -> None:
        state = _sample_state()
        desc = update_description_with_workflow_state(
            "Body line 1\nBody line 2\n", state
        )
        assert "Body line 1" in desc
        assert "Body line 2" in desc

    def test_handles_required_question_shape(self) -> None:
        state = _sample_state()
        state = state.model_copy(
            update={
                "questions": [
                    ModelWorkflowQuestion(
                        id="q1", text="Which path?", required=True, answer=None
                    )
                ]
            }
        )
        desc = update_description_with_workflow_state("Body.", state)
        parsed = extract_workflow_state(desc)
        assert parsed is not None
        assert parsed.is_questions_complete() is False


@pytest.mark.unit
class TestPersistWorkflowStateLocally:
    def test_honors_onex_state_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_STATE_DIR", str(tmp_path))
        state = _sample_state()
        persist_workflow_state_locally("OMN-1234", state)
        contract_path = tmp_path / "tickets" / "OMN-1234" / "contract.yaml"
        assert contract_path.exists()
        parsed = yaml.safe_load(contract_path.read_text())
        assert parsed["ticket_id"] == "OMN-1234"

    def test_falls_back_to_home_onex_state_when_env_unset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ONEX_STATE_DIR", raising=False)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        state = _sample_state()
        persist_workflow_state_locally("OMN-1234", state)
        contract_path = (
            tmp_path / ".onex_state" / "tickets" / "OMN-1234" / "contract.yaml"
        )
        assert contract_path.exists()

    def test_never_writes_to_tilde_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Fake a home containing a .claude/tickets/ tree; persist must not
        # touch it under any env-var configuration.
        fake_home = tmp_path / "home"
        claude_dir = fake_home / ".claude" / "tickets"
        claude_dir.mkdir(parents=True)
        sentinel = claude_dir / "sentinel.txt"
        sentinel.write_text("untouched")

        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        monkeypatch.setenv("ONEX_STATE_DIR", str(tmp_path / "custom_state"))

        persist_workflow_state_locally("OMN-1234", _sample_state())

        # Sentinel preserved.
        assert sentinel.read_text() == "untouched"
        # Nothing written under ~/.claude/tickets for this ticket.
        assert not (claude_dir / "OMN-1234").exists()
        # Write landed under ONEX_STATE_DIR.
        assert (
            tmp_path / "custom_state" / "tickets" / "OMN-1234" / "contract.yaml"
        ).exists()

    def test_is_atomic_via_tmp_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_STATE_DIR", str(tmp_path))
        state = _sample_state()
        persist_workflow_state_locally("OMN-1234", state)
        target_dir = tmp_path / "tickets" / "OMN-1234"
        # No leftover .tmp sibling after successful write.
        assert not any(p.suffix == ".tmp" for p in target_dir.iterdir())

    def test_overwrites_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_STATE_DIR", str(tmp_path))
        state_a = _sample_state(phase="intake")
        persist_workflow_state_locally("OMN-1234", state_a)
        state_b = state_a.model_copy(update={"phase": EnumTicketWorkflowPhase.DONE})
        persist_workflow_state_locally("OMN-1234", state_b)
        contract_path = tmp_path / "tickets" / "OMN-1234" / "contract.yaml"
        parsed = yaml.safe_load(contract_path.read_text())
        assert parsed["phase"] == "done"


@pytest.mark.unit
class TestTicketIdValidation:
    """``ticket_id`` must be a single relative path segment (path-traversal guard)."""

    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "..",
            ".",
            "../escape",
            "/etc/passwd",
            "nested/OMN-1",
            "back\\slash",
        ],
    )
    def test_rejects_unsafe_ticket_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_id: str
    ) -> None:
        monkeypatch.setenv("ONEX_STATE_DIR", str(tmp_path))
        with pytest.raises(ModelOnexError, match="ticket_id must be a single"):
            persist_workflow_state_locally(bad_id, _sample_state())


@pytest.mark.unit
class TestClaudeRootRejection:
    """``_tickets_dir`` must reject any config that resolves under ``~/.claude``."""

    def test_rejects_direct_claude_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        monkeypatch.setenv("ONEX_STATE_DIR", str(fake_home / ".claude"))
        with pytest.raises(ModelOnexError, match=r"must not point to ~/\.claude"):
            persist_workflow_state_locally("OMN-1234", _sample_state())

    def test_rejects_claude_subdir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        monkeypatch.setenv("ONEX_STATE_DIR", str(fake_home / ".claude" / "nested"))
        with pytest.raises(ModelOnexError, match=r"must not point to ~/\.claude"):
            persist_workflow_state_locally("OMN-1234", _sample_state())
