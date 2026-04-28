# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for extended ModelDodEvidenceCheck fields (OMN-10241, Wave 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)


@pytest.mark.unit
class TestModelDodEvidenceCheckExtended:
    def test_grep_check_type_with_dict_value_validates(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="grep",
            check_value={"pattern": "foo", "path": "bar"},
        )
        assert check.check_type == "grep"
        assert check.check_value == {"pattern": "foo", "path": "bar"}

    def test_unknown_check_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ModelDodEvidenceCheck(
                check_type="unknown_type",
                check_value="some_value",
            )

    def test_cwd_template_token_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="command",
            check_value="uv run pytest",
            cwd="${OMNI_HOME}/some_repo",
        )
        assert check.cwd == "${OMNI_HOME}/some_repo"

    def test_cwd_defaults_to_none(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="command",
            check_value="uv run pytest",
        )
        assert check.cwd is None

    def test_existing_command_check_type_with_str_value_still_validates(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="command",
            check_value="pytest",
        )
        assert check.check_type == "command"
        assert check.check_value == "pytest"

    def test_all_six_literal_check_types_accepted(self) -> None:
        valid_types = [
            "test_exists",
            "test_passes",
            "file_exists",
            "grep",
            "command",
            "endpoint",
        ]
        for ct in valid_types:
            check = ModelDodEvidenceCheck(check_type=ct, check_value="val")
            assert check.check_type == ct

    def test_check_value_str_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="command", check_value="uv run mypy src/"
        )
        assert isinstance(check.check_value, str)

    def test_check_value_dict_str_str_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="grep",
            check_value={"pattern": "OMN-10241", "path": "src/"},
        )
        assert isinstance(check.check_value, dict)

    def test_check_value_invalid_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ModelDodEvidenceCheck(
                check_type="command",
                check_value=12345,  # type: ignore[arg-type]
            )

    def test_cwd_pr_number_token_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="endpoint",
            check_value="http://localhost:8080/health",
            cwd="${PR_NUMBER}",
        )
        assert check.cwd == "${PR_NUMBER}"

    def test_cwd_repo_token_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="file_exists",
            check_value="docs/plans/some-plan.md",
            cwd="${REPO}/docs",
        )
        assert check.cwd == "${REPO}/docs"

    def test_cwd_ticket_id_token_accepted(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="test_passes",
            check_value="tests/unit/test_foo.py",
            cwd="${TICKET_ID}",
        )
        assert check.cwd == "${TICKET_ID}"
