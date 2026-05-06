# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelDelegationRequest and EnumRedactionPolicy (OMN-10609)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_redaction_policy import EnumRedactionPolicy
from omnibase_core.models.delegation.model_delegation_request import (
    ModelDelegationRequest,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

_CAUSATION_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")

_MINIMAL_KWARGS: dict[str, object] = {
    "causation_id": _CAUSATION_ID,
    "session_id": "sess-abc123",
    "tool_use_id": "tu-xyz789",
    "hook_name": "PreToolUse",
    "tool_name": "Bash",
    "task_type": "compute",
    "input_hash": "sha256:deadbeef",
}


@pytest.mark.unit
class TestEnumRedactionPolicy:
    def test_values(self) -> None:
        assert EnumRedactionPolicy.REDACT.value == "redact"
        assert EnumRedactionPolicy.HASH_ONLY.value == "hash_only"
        assert EnumRedactionPolicy.FULL_CAPTURE.value == "full_capture"

    def test_is_str_subclass(self) -> None:
        assert isinstance(EnumRedactionPolicy.REDACT, str)


@pytest.mark.unit
class TestModelDelegationRequest:
    def test_minimal_instantiation(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert req.causation_id == _CAUSATION_ID
        assert req.session_id == "sess-abc123"
        assert req.tool_name == "Bash"
        assert req.input_hash == "sha256:deadbeef"

    def test_envelope_id_auto_generated(self) -> None:
        r1 = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        r2 = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert r1.envelope_id != r2.envelope_id

    def test_correlation_id_auto_generated(self) -> None:
        r1 = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        r2 = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert r1.correlation_id != r2.correlation_id

    def test_default_redaction_policy(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert req.input_redaction_policy is EnumRedactionPolicy.HASH_ONLY

    def test_explicit_redaction_policy(self) -> None:
        req = ModelDelegationRequest(
            **_MINIMAL_KWARGS,  # type: ignore[arg-type]
            input_redaction_policy=EnumRedactionPolicy.FULL_CAPTURE,
        )
        assert req.input_redaction_policy is EnumRedactionPolicy.FULL_CAPTURE

    def test_requested_at_default_is_utc(self) -> None:
        before = datetime.now(tz=UTC)
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        after = datetime.now(tz=UTC)
        assert before <= req.requested_at <= after

    def test_contract_version_default(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        assert req.contract_version == ModelSemVer(major=1, minor=0, patch=0)

    def test_explicit_envelope_id(self) -> None:
        fixed_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        req = ModelDelegationRequest(
            **_MINIMAL_KWARGS,  # type: ignore[arg-type]
            envelope_id=fixed_id,
        )
        assert req.envelope_id == fixed_id

    def test_frozen(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValidationError)):
            req.tool_name = "Edit"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationRequest(
                **_MINIMAL_KWARGS,  # type: ignore[arg-type]
                unknown_field="boom",
            )

    def test_causation_id_required(self) -> None:
        kwargs = {k: v for k, v in _MINIMAL_KWARGS.items() if k != "causation_id"}
        with pytest.raises(ValidationError):
            ModelDelegationRequest(**kwargs)  # type: ignore[arg-type]

    def test_round_trip_serialization(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        data = req.model_dump(mode="json")
        restored = ModelDelegationRequest.model_validate(data)
        assert restored == req

    def test_json_string_round_trip(self) -> None:
        req = ModelDelegationRequest(**_MINIMAL_KWARGS)  # type: ignore[arg-type]
        json_str = req.model_dump_json()
        restored = ModelDelegationRequest.model_validate_json(json_str)
        assert restored == req
