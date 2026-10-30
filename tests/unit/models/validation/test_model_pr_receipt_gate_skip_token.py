# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPrReceiptGateSkipToken (OMN-14187)."""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_pr_receipt_gate_skip_token import (
    ModelPrReceiptGateSkipToken,
)

# Regression pin copied verbatim from
# omniclaude/.pre-commit-hooks/reject-deploy-gate-skip-token.sh so that any drift
# in the rendered token shape breaks this test.
_HOOK_SKIP_PATTERN = re.compile(r"\[skip-[a-zA-Z]", re.IGNORECASE)


@pytest.mark.unit
class TestModelPrReceiptGateSkipToken:
    def test_valid_construction(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="receipt-gate", reason="docs only"
        )
        assert token.gate_name == "receipt-gate"
        assert token.reason == "docs only"

    @pytest.mark.parametrize("bad_name", ["has space", "1leading-digit", "-dash"])
    def test_invalid_gate_name_pattern_raises(self, bad_name: str) -> None:
        with pytest.raises(ValidationError):
            ModelPrReceiptGateSkipToken(gate_name=bad_name)

    def test_empty_gate_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrReceiptGateSkipToken(gate_name="")

    def test_no_allowlist_state_exists(self) -> None:
        """OMN-20074: the approvals registry is retired, so a token carries no receipt id."""
        assert "allowlist_receipt_id" not in ModelPrReceiptGateSkipToken.model_fields
        assert not hasattr(
            ModelPrReceiptGateSkipToken(gate_name="deploy-gate"), "is_allowlisted"
        )
        with pytest.raises(ValidationError):
            ModelPrReceiptGateSkipToken.model_validate(
                {"gate_name": "deploy-gate", "allowlist_receipt_id": "approval-abc123"}
            )

    def test_render_token_exact_format(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="deploy-gate", reason="correctness fix"
        )
        assert token.render_token() == "[skip-deploy-gate: correctness fix]"

    def test_rendered_token_matches_hook_skip_pattern(self) -> None:
        # The rendered token must be detectable by the pre-commit / CI hook.
        token = ModelPrReceiptGateSkipToken(gate_name="receipt-gate", reason="x")
        assert _HOOK_SKIP_PATTERN.search(token.render_token()) is not None

    def test_serialization_roundtrip(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="receipt-gate",
            reason="ticketless chore",
        )
        restored = ModelPrReceiptGateSkipToken.model_validate(token.model_dump())
        assert restored == token
        restored_json = ModelPrReceiptGateSkipToken.model_validate_json(
            token.model_dump_json()
        )
        assert restored_json == token

    def test_frozen_attribute_mutation_raises(self) -> None:
        token = ModelPrReceiptGateSkipToken(gate_name="receipt-gate")
        with pytest.raises(ValidationError):
            setattr(token, "reason", "changed")

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrReceiptGateSkipToken.model_validate(
                {"gate_name": "receipt-gate", "nested_allowlist": "x"}
            )

    def test_to_json_deterministic(self) -> None:
        token = ModelPrReceiptGateSkipToken(gate_name="receipt-gate", reason="r")
        assert token.to_json() == token.to_json()
