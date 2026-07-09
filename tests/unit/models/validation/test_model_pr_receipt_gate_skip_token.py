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

# Regression pins copied verbatim from
# omniclaude/.pre-commit-hooks/reject-deploy-gate-skip-token.sh so that any drift
# in the rendered token / allowlist companion shape breaks this test.
_HOOK_SKIP_PATTERN = re.compile(r"\[skip-[a-zA-Z]", re.IGNORECASE)
_HOOK_ALLOWLIST_PATTERN = re.compile(r"#\s*skip-token-allowed:\s*\S", re.IGNORECASE)


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

    def test_allowlist_default_none_not_allowlisted(self) -> None:
        token = ModelPrReceiptGateSkipToken(gate_name="deploy-gate")
        assert token.allowlist_receipt_id is None
        assert token.is_allowlisted is False

    def test_allowlist_set_is_allowlisted(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="deploy-gate", allowlist_receipt_id="approval-abc123"
        )
        assert token.is_allowlisted is True

    def test_render_token_exact_format(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="deploy-gate", reason="correctness fix"
        )
        assert token.render_token() == "[skip-deploy-gate: correctness fix]"

    def test_rendered_token_matches_hook_skip_pattern(self) -> None:
        # The rendered token must be detectable by the pre-commit / CI hook.
        token = ModelPrReceiptGateSkipToken(gate_name="receipt-gate", reason="x")
        assert _HOOK_SKIP_PATTERN.search(token.render_token()) is not None

    def test_allowlist_companion_line_matches_hook_pattern(self) -> None:
        # The out-of-band companion line the hook scans for.
        companion = "# skip-token-allowed: approval-abc123"
        assert _HOOK_ALLOWLIST_PATTERN.search(companion) is not None

    def test_serialization_roundtrip(self) -> None:
        token = ModelPrReceiptGateSkipToken(
            gate_name="receipt-gate",
            reason="ticketless chore",
            allowlist_receipt_id="rid-1",
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
            token.reason = "changed"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrReceiptGateSkipToken(
                gate_name="receipt-gate",
                nested_allowlist="x",  # type: ignore[call-arg]
            )

    def test_to_json_deterministic(self) -> None:
        token = ModelPrReceiptGateSkipToken(gate_name="receipt-gate", reason="r")
        assert token.to_json() == token.to_json()
