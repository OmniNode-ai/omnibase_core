# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDodEvidenceCheck extended fields (OMN-10066 / OMN-9582).

OMN-10066 extends ModelDodEvidenceCheck to match OCC ModelDodCheck field shapes:
  - check_value accepts str | dict[str, str] (dict form for 'grep' check type)
  - cwd field added (OMN-10078) for optional working directory

Coverage per plan Task 4:
  1. OCC construction: ModelDodEvidenceCheck with dict check_value succeeds.
  2. String check_value still works (no regression for PR-gate callers).
  3. check_value as dict with pattern + path round-trips cleanly.
  4. cwd defaults to None when not provided.
  5. cwd accepts template token strings.
  6. cwd explicit None is valid.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)


@pytest.mark.unit
class TestModelDodEvidenceCheckDictValue:
    """check_value as dict[str, str] — for 'grep' check type."""

    def test_dict_check_value_accepted(self) -> None:
        """OCC construction: grep check with dict value succeeds."""
        check = ModelDodEvidenceCheck.model_validate(
            {
                "check_type": "grep",
                "check_value": {"pattern": "class ModelDodCheck", "path": "src/"},
            }
        )
        assert isinstance(check.check_value, dict)
        assert check.check_value["pattern"] == "class ModelDodCheck"
        assert check.check_value["path"] == "src/"

    def test_string_check_value_still_accepted(self) -> None:
        """PR-gate callers using string check_value are unaffected."""
        check = ModelDodEvidenceCheck(
            check_type="command",
            check_value="uv run pytest tests/ -v",
        )
        assert check.check_value == "uv run pytest tests/ -v"

    def test_dict_check_value_round_trips(self) -> None:
        """Dict check_value serializes and deserializes without loss."""
        original = ModelDodEvidenceCheck.model_validate(
            {
                "check_type": "grep",
                "check_value": {"pattern": "def test_", "path": "tests/"},
            }
        )
        dumped = original.model_dump()
        restored = ModelDodEvidenceCheck.model_validate(dumped)
        assert restored.check_value == {"pattern": "def test_", "path": "tests/"}


@pytest.mark.unit
class TestModelDodEvidenceCheckCwdField:
    """cwd field — OMN-10078 optional working directory for check execution."""

    def test_cwd_defaults_to_none(self) -> None:
        """cwd defaults to None so existing contracts are unaffected."""
        check = ModelDodEvidenceCheck(
            check_type="command",
            check_value="pytest",
        )
        assert check.cwd is None

    def test_cwd_accepts_string_value(self) -> None:
        check = ModelDodEvidenceCheck.model_validate(
            {
                "check_type": "command",
                "check_value": "pytest",
                "cwd": "${OMNI_HOME}/omnibase_core",
            }
        )
        assert check.cwd == "${OMNI_HOME}/omnibase_core"

    def test_cwd_accepts_template_tokens(self) -> None:
        """Runner expands ${PR_NUMBER}/${REPO}/${TICKET_ID}; model stores raw."""
        check = ModelDodEvidenceCheck.model_validate(
            {
                "check_type": "command",
                "check_value": "gh pr checks ${PR_NUMBER}",
                "cwd": "${OMNI_HOME}/${REPO}",
            }
        )
        assert check.cwd == "${OMNI_HOME}/${REPO}"

    def test_cwd_explicit_none_is_valid(self) -> None:
        check = ModelDodEvidenceCheck.model_validate(
            {"check_type": "command", "check_value": "pytest", "cwd": None}
        )
        assert check.cwd is None

    def test_check_type_empty_string_rejected(self) -> None:
        """check_type min_length=1 still enforced."""
        with pytest.raises(ValidationError):
            ModelDodEvidenceCheck(check_type="", check_value="something")
