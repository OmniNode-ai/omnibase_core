# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractDodItem with extended ModelDodEvidenceCheck fields (OMN-10242, Wave 1 Task 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem


@pytest.mark.unit
class TestModelContractDodItemExtendedChecks:
    def test_grep_check_type_with_dict_check_value_validates(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type=EnumDodCheckType.GREP,
            check_value={"pattern": "x", "path": "y"},
        )
        item = ModelContractDodItem(
            id="dod-001",
            description="grep check passes",
            checks=[check],
        )
        assert len(item.checks) == 1
        assert item.checks[0].check_type == EnumDodCheckType.GREP
        assert item.checks[0].check_value == {"pattern": "x", "path": "y"}

    def test_grep_check_type_with_string_literal_validates(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type="grep",
            check_value={"pattern": "OMN-10242", "path": "src/"},
        )
        item = ModelContractDodItem(
            id="dod-002",
            description="grep with string literal check_type",
            checks=[check],
        )
        assert item.checks[0].check_type == "grep"

    def test_status_verified_is_accepted(self) -> None:
        item = ModelContractDodItem(
            id="dod-003",
            description="verified item",
            status="verified",
        )
        assert item.status == "verified"

    def test_source_linear_is_accepted(self) -> None:
        item = ModelContractDodItem(
            id="dod-004",
            description="linear-sourced item",
            source="linear",
        )
        assert item.source == "linear"

    def test_status_default_is_pending(self) -> None:
        item = ModelContractDodItem(
            id="dod-005",
            description="default status item",
        )
        assert item.status == "pending"

    def test_source_default_is_generated(self) -> None:
        item = ModelContractDodItem(
            id="dod-006",
            description="default source item",
        )
        assert item.source == "generated"

    def test_check_with_cwd_template_token_validates(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type=EnumDodCheckType.COMMAND,
            check_value="uv run pytest tests/",
            cwd="${OMNI_HOME}/omnibase_core",
        )
        item = ModelContractDodItem(
            id="dod-007",
            description="check with cwd template token",
            checks=[check],
        )
        assert item.checks[0].cwd == "${OMNI_HOME}/omnibase_core"

    def test_multiple_checks_with_mixed_check_value_types_validate(self) -> None:
        checks = [
            ModelDodEvidenceCheck(
                check_type=EnumDodCheckType.GREP,
                check_value={"pattern": "ModelContractDodItem", "path": "src/"},
            ),
            ModelDodEvidenceCheck(
                check_type=EnumDodCheckType.COMMAND,
                check_value="uv run pytest tests/unit/ -v",
            ),
        ]
        item = ModelContractDodItem(
            id="dod-008",
            description="multiple checks mixed types",
            status="verified",
            source="linear",
            checks=checks,
        )
        assert len(item.checks) == 2
        assert isinstance(item.checks[0].check_value, dict)
        assert isinstance(item.checks[1].check_value, str)

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractDodItem(
                id="dod-009",
                description="invalid status",
                status="approved",  # type: ignore[arg-type]
            )

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractDodItem(
                id="dod-010",
                description="invalid source",
                source="unknown",  # type: ignore[arg-type]
            )

    def test_empty_checks_list_is_valid(self) -> None:
        item = ModelContractDodItem(
            id="dod-011",
            description="no checks",
        )
        assert item.checks == []

    def test_all_status_literals_accepted(self) -> None:
        for status in ("pending", "verified", "failed", "skipped"):
            item = ModelContractDodItem(
                id=f"dod-{status}",
                description=f"status {status}",
                status=status,  # type: ignore[arg-type]
            )
            assert item.status == status

    def test_all_source_literals_accepted(self) -> None:
        for source in ("linear", "manual", "generated"):
            item = ModelContractDodItem(
                id=f"dod-src-{source}",
                description=f"source {source}",
                source=source,  # type: ignore[arg-type]
            )
            assert item.source == source

    def test_check_with_cwd_none_is_default(self) -> None:
        check = ModelDodEvidenceCheck(
            check_type=EnumDodCheckType.FILE_EXISTS,
            check_value="docs/plans/some-plan.md",
        )
        item = ModelContractDodItem(
            id="dod-012",
            description="check with no cwd",
            checks=[check],
        )
        assert item.checks[0].cwd is None

    def test_semantic_grading_check_type_accepted(self) -> None:
        """OMN-10859: SEMANTIC_GRADING check type accepted by ModelDodEvidenceCheck."""
        check = ModelDodEvidenceCheck(
            check_type=EnumDodCheckType.SEMANTIC_GRADING,
            check_value="drift/dod_receipts/OMN-10859/dod-001/semantic_grading.yaml",
        )
        item = ModelContractDodItem(
            id="dod-013",
            description="Acceptance criteria semantically satisfied (advisory Phase 1)",
            source="generated",
            checks=[check],
        )
        assert item.checks[0].check_type == EnumDodCheckType.SEMANTIC_GRADING
        assert item.checks[0].check_type == "semantic_grading"
