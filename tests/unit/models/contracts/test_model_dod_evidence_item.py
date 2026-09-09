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


# -- OMN-18056: the acceptance-criterion binding ---------------------------


def test_binds_ac_defaults_to_empty_so_the_whole_corpus_keeps_parsing() -> None:
    """8709 existing contracts declare no binding; none of them may break.

    The field is the enabling half of OMN-18056 and it is additive by
    construction: an item that says nothing about acceptance criteria is still
    a valid item, it just covers none of them — which is a coverage gap for
    the consumer to report, never a parse error here.
    """
    item = ModelDodEvidenceItem(
        id="dod-1",
        description="tests pass",
        checks=[ModelDodEvidenceCheck(check_type="test_passes", check_value="pytest")],
    )
    assert item.binds_ac == ()


def test_a_contract_can_declare_which_criteria_an_item_covers() -> None:
    """THE RECORDED DEFECT, at the layer that made it unfixable.

    Before this field, ``extra="forbid"`` meant a contract that TRIED to state
    which criterion an evidence item proves would fail to parse — so the
    relation was not merely undeclared across the corpus, it was undeclarable,
    and the only question a consumer could ask of a green verdict was how many
    checks passed.
    """
    item = ModelDodEvidenceItem(
        id="dod-tests",
        description="terminal isolation covered on both call sites",
        checks=[ModelDodEvidenceCheck(check_type="test_passes", check_value="pytest")],
        binds_ac=("AC2", "AC3"),
    )
    assert item.binds_ac == ("AC2", "AC3")


def test_an_undeclared_field_is_still_refused() -> None:
    """`extra="forbid"` stays. It is why the field was needed, not a defect."""
    with pytest.raises(ValidationError):
        ModelDodEvidenceItem(
            id="dod-1",
            description="x",
            checks=[
                ModelDodEvidenceCheck(check_type="test_passes", check_value="pytest")
            ],
            binds_acceptance_criteria=("AC1",),  # type: ignore[call-arg]
        )


def test_the_governance_item_model_carries_the_same_binding() -> None:
    """Both item models own the field, because both gate on the field set.

    ``ModelContractDodItem`` is what the DoD verifier validates a contract's
    items against; a binding declared only on the receipt-gate model would be
    rejected THERE as an unknown field, so a contract could not carry it at
    all. One meaning, two owners, added together.
    """
    from omnibase_core.models.ticket.model_contract_dod_item import (
        ModelContractDodItem,
    )

    assert ModelContractDodItem(id="dod-1", description="x").binds_ac == ()
    assert ModelContractDodItem(
        id="dod-1", description="x", binds_ac=("AC1",)
    ).binds_ac == ("AC1",)
