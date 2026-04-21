# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelReducerFsmMetadata (7-key FSM metadata contract).

Test Coverage:
    - Instantiation with minimal (required-only) and full (all 7 keys) fields
    - Default values for all optional fields
    - Round-trip via to_dict / from_dict
    - Rejection of extra keys (extra='forbid')
    - Rejection of wrong types (fsm_transition_success: bool required)
    - Frozen / immutability behavior
    - Distinction between failure_reason (expected) and error (unexpected)

Architecture Context:
    ModelReducerFsmMetadata encodes the 7-key FSM metadata contract declared
    in CONTRACT_DRIVEN_NODEREDUCER_V1_0.md / V1_0_4_DELTA.md. It supplies a
    typed alternative to dict-based metadata so downstream consumers
    (dashboards, replay, verification) see a schema-validated shape.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer import ModelReducerFsmMetadata
from omnibase_core.models.reducer.model_reducer_fsm_metadata import (
    ModelReducerFsmMetadata as DirectImport,
)

pytestmark = pytest.mark.unit


class TestInstantiation:
    """Basic instantiation paths for the 7-key contract."""

    def test_minimal_required_fields(self) -> None:
        """Only fsm_state and fsm_transition_success are required."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="IDLE",
            fsm_transition_success=True,
        )
        assert metadata.fsm_state == "IDLE"
        assert metadata.fsm_transition_success is True
        # Optional fields default to None
        assert metadata.fsm_previous_state is None
        assert metadata.fsm_transition_name is None
        assert metadata.failure_reason is None
        assert metadata.failed_conditions is None
        assert metadata.error is None

    def test_full_success_payload(self) -> None:
        """All 7 keys populated for a successful transition."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="PROCESSING",
            fsm_previous_state="PENDING",
            fsm_transition_success=True,
            fsm_transition_name="start_processing",
            failure_reason=None,
            failed_conditions=None,
            error=None,
        )
        assert metadata.fsm_previous_state == "PENDING"
        assert metadata.fsm_transition_name == "start_processing"

    def test_full_failure_payload(self) -> None:
        """All 7 keys populated for a failed transition."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="PENDING",
            fsm_previous_state="PENDING",
            fsm_transition_success=False,
            fsm_transition_name="start_processing",
            failure_reason="Guard not satisfied",
            failed_conditions=["has_input_data", "queue_not_full"],
            error=None,
        )
        assert metadata.fsm_transition_success is False
        assert metadata.failure_reason == "Guard not satisfied"
        assert metadata.failed_conditions == ("has_input_data", "queue_not_full")

    def test_error_field_for_unexpected_exception(self) -> None:
        """`error` is distinct from `failure_reason` and carries exception text."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="PENDING",
            fsm_previous_state="PENDING",
            fsm_transition_success=False,
            error="KeyError: 'missing_key'",
        )
        assert metadata.error == "KeyError: 'missing_key'"
        assert metadata.failure_reason is None

    def test_direct_import_matches_package_import(self) -> None:
        """Both import paths resolve to the same class."""
        assert DirectImport is ModelReducerFsmMetadata


class TestValidation:
    """Validation behavior from ConfigDict(frozen, extra='forbid')."""

    def test_rejects_extra_keys(self) -> None:
        """extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError):
            ModelReducerFsmMetadata(
                fsm_state="IDLE",
                fsm_transition_success=True,
                unknown_key="should-be-rejected",  # type: ignore[call-arg]
            )

    def test_requires_fsm_state(self) -> None:
        with pytest.raises(ValidationError):
            ModelReducerFsmMetadata(fsm_transition_success=True)  # type: ignore[call-arg]

    def test_requires_fsm_transition_success(self) -> None:
        with pytest.raises(ValidationError):
            ModelReducerFsmMetadata(fsm_state="IDLE")  # type: ignore[call-arg]

    def test_rejects_wrong_success_type(self) -> None:
        """fsm_transition_success is a bool; a string that isn't coercible fails."""
        with pytest.raises(ValidationError):
            ModelReducerFsmMetadata(
                fsm_state="IDLE",
                fsm_transition_success="not-a-bool",  # type: ignore[arg-type]
            )

    def test_rejects_non_sequence_failed_conditions(self) -> None:
        with pytest.raises(ValidationError):
            ModelReducerFsmMetadata(
                fsm_state="IDLE",
                fsm_transition_success=False,
                failed_conditions="guard_a",  # type: ignore[arg-type]
            )

    def test_accepts_list_failed_conditions_coerced_to_tuple(self) -> None:
        """List input is coerced to tuple for immutability."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="IDLE",
            fsm_transition_success=False,
            failed_conditions=["guard_a", "guard_b"],
        )
        assert metadata.failed_conditions == ("guard_a", "guard_b")
        assert isinstance(metadata.failed_conditions, tuple)

    def test_accepts_empty_failed_conditions(self) -> None:
        """An empty tuple is a legal value — distinct from None."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="IDLE",
            fsm_transition_success=False,
            failed_conditions=[],
        )
        assert metadata.failed_conditions == ()


class TestFrozen:
    """ConfigDict(frozen=True) immutability."""

    def test_cannot_mutate_fields(self) -> None:
        metadata = ModelReducerFsmMetadata(
            fsm_state="IDLE",
            fsm_transition_success=True,
        )
        with pytest.raises(ValidationError):
            metadata.fsm_state = "RUNNING"  # type: ignore[misc]


class TestRoundTrip:
    """to_dict / from_dict round-trip for the 7-key contract."""

    def test_roundtrip_preserves_full_payload(self) -> None:
        original = ModelReducerFsmMetadata(
            fsm_state="DONE",
            fsm_previous_state="PROCESSING",
            fsm_transition_success=True,
            fsm_transition_name="complete",
            failure_reason=None,
            failed_conditions=None,
            error=None,
        )
        restored = ModelReducerFsmMetadata.from_dict(original.to_dict())
        assert restored == original

    def test_roundtrip_preserves_failure_payload(self) -> None:
        original = ModelReducerFsmMetadata(
            fsm_state="PENDING",
            fsm_previous_state="PENDING",
            fsm_transition_success=False,
            fsm_transition_name="start",
            failure_reason="Guard failed",
            failed_conditions=("has_input",),
            error=None,
        )
        restored = ModelReducerFsmMetadata.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_contains_all_seven_keys(self) -> None:
        """to_dict must emit the fixed 7-key shape (None preserved)."""
        metadata = ModelReducerFsmMetadata(
            fsm_state="IDLE",
            fsm_transition_success=True,
        )
        payload = metadata.to_dict()
        expected_keys = {
            "fsm_state",
            "fsm_previous_state",
            "fsm_transition_success",
            "fsm_transition_name",
            "failure_reason",
            "failed_conditions",
            "error",
        }
        assert set(payload.keys()) == expected_keys

    def test_from_dict_rejects_extra_keys(self) -> None:
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        with pytest.raises((ModelOnexError, ValidationError)):
            ModelReducerFsmMetadata.from_dict(
                {
                    "fsm_state": "IDLE",
                    "fsm_transition_success": True,
                    "unexpected": "value",
                }
            )

    def test_from_dict_requires_all_7_keys(self) -> None:
        """from_dict enforces the 7-key contract — partial dicts are rejected."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        with pytest.raises(ModelOnexError, match="missing"):
            ModelReducerFsmMetadata.from_dict(
                {"fsm_state": "IDLE", "fsm_transition_success": True}
            )

    def test_from_dict_accepts_none_optionals_when_all_keys_present(self) -> None:
        """from_dict accepts all 7 keys with None for optional fields."""
        metadata = ModelReducerFsmMetadata.from_dict(
            {
                "fsm_state": "IDLE",
                "fsm_previous_state": None,
                "fsm_transition_success": True,
                "fsm_transition_name": None,
                "failure_reason": None,
                "failed_conditions": None,
                "error": None,
            }
        )
        assert metadata.fsm_previous_state is None
        assert metadata.fsm_transition_name is None
        assert metadata.failure_reason is None
        assert metadata.failed_conditions is None
        assert metadata.error is None
