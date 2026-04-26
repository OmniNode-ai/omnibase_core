# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDodEvidenceItem (OMN-9787).

`file_exists` is structurally weak proof: when the only declared check on a
dod_evidence item is `file_exists` and the path points at the receipt itself,
the receipt becomes its own evidence — a tautology. The contract-side validator
in `ModelDodEvidenceItem` must reject items whose sole `check_type` is
`file_exists` so the anti-pattern cannot be encoded in any new contract.

The validator is pure (no I/O); allowlist / exemption logic for legacy
contracts lives in the gate (Task 8), not here.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)


@pytest.mark.unit
class TestModelDodEvidenceItemSoleFileExistsRejection:
    """An item whose only check is `file_exists` must fail validation."""

    def test_evidence_item_with_only_file_exists_check_rejects(self) -> None:
        with pytest.raises(ValidationError) as ei:
            ModelDodEvidenceItem(
                id="dod-001",
                description="OMN-9787 sole file_exists must be rejected",
                checks=[
                    ModelDodEvidenceCheck(
                        check_type="file_exists",
                        check_value=(
                            "drift/dod_receipts/OMN-9787/dod-001/file_exists.yaml"
                        ),
                    ),
                ],
            )
        message = str(ei.value).lower()
        assert "file_exists" in message
        assert "sole" in message or "weak" in message

    def test_error_message_contains_machine_token(self) -> None:
        """Gate (Task 8) keys exemption logic on the stable token, not prose."""
        with pytest.raises(ValidationError) as ei:
            ModelDodEvidenceItem(
                id="dod-001",
                description="token-bearing rejection",
                checks=[
                    ModelDodEvidenceCheck(
                        check_type="file_exists",
                        check_value=(
                            "drift/dod_receipts/OMN-9787/dod-001/file_exists.yaml"
                        ),
                    ),
                ],
            )
        assert "DOD_EVIDENCE_FILE_EXISTS_SOLE_CHECK" in str(ei.value)

    def test_multiple_file_exists_checks_still_rejected(self) -> None:
        """Stacking `file_exists` checks does not satisfy the rule."""
        with pytest.raises(ValidationError) as ei:
            ModelDodEvidenceItem(
                id="dod-multi",
                description="multiple file_exists is still sole-type",
                checks=[
                    ModelDodEvidenceCheck(
                        check_type="file_exists",
                        check_value="drift/a.yaml",
                    ),
                    ModelDodEvidenceCheck(
                        check_type="file_exists",
                        check_value="drift/b.yaml",
                    ),
                ],
            )
        assert "DOD_EVIDENCE_FILE_EXISTS_SOLE_CHECK" in str(ei.value)


@pytest.mark.unit
class TestModelDodEvidenceItemAcceptedShapes:
    """Items with at least one stronger check_type are accepted."""

    def test_evidence_item_with_file_exists_paired_with_command_passes(self) -> None:
        item = ModelDodEvidenceItem(
            id="dod-002",
            description="file_exists alongside command is acceptable",
            checks=[
                ModelDodEvidenceCheck(
                    check_type="file_exists",
                    check_value="drift/dod_receipts/OMN-9787/dod-002/file_exists.yaml",
                ),
                ModelDodEvidenceCheck(
                    check_type="command",
                    check_value="gh pr checks 916 --repo OmniNode-ai/omnibase_core",
                ),
            ],
        )
        types = {c.check_type for c in item.checks}
        assert types == {"file_exists", "command"}

    def test_evidence_item_with_only_command_check_passes(self) -> None:
        item = ModelDodEvidenceItem(
            id="dod-003",
            description="command alone is acceptable",
            checks=[
                ModelDodEvidenceCheck(
                    check_type="command",
                    check_value="uv run pytest tests/unit -v",
                ),
            ],
        )
        assert item.checks[0].check_type == "command"

    @pytest.mark.parametrize(
        "stronger_check_type",
        ["command", "test_passes", "endpoint", "grep", "test_exists"],
    )
    def test_evidence_item_with_file_exists_paired_with_any_strong_check(
        self, stronger_check_type: str
    ) -> None:
        """Pairing file_exists with any of the recognized stronger types is OK."""
        item = ModelDodEvidenceItem(
            id="dod-pair",
            description=f"file_exists paired with {stronger_check_type}",
            checks=[
                ModelDodEvidenceCheck(
                    check_type="file_exists",
                    check_value="drift/dod_receipts/OMN-9787/dod-pair/file.yaml",
                ),
                ModelDodEvidenceCheck(
                    check_type=stronger_check_type,
                    check_value="some-stronger-probe",
                ),
            ],
        )
        assert any(c.check_type == stronger_check_type for c in item.checks)

    def test_evidence_item_with_no_checks_does_not_trigger_sole_rule(self) -> None:
        """Empty checks list is not a sole-file_exists violation; other surfaces
        (the parent contract's `min_length=1` on `dod_evidence`) handle empty
        intent. The validator only flags the specific tautology pattern.
        """
        item = ModelDodEvidenceItem(
            id="dod-empty",
            description="no checks declared",
            checks=[],
        )
        assert item.checks == []
