# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Production regressions for secure-envelope signature audit atomicity."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.core.model_route_spec import ModelRouteSpec
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_secure_event_envelope_class import (
    ModelSecureEventEnvelope,
)
from omnibase_core.models.security.model_signature_chain import ModelSignatureChain


def _envelope_and_signature() -> tuple[ModelSecureEventEnvelope, ModelNodeSignature]:
    node_id = uuid4()
    envelope = ModelSecureEventEnvelope(
        payload=ModelOnexEvent(
            event_type="core.node.start",
            node_id=node_id,
            timestamp=datetime.now(UTC),
            event_id=uuid4(),
        ),
        route_spec=ModelRouteSpec.create_direct_route(f"node://{uuid4()}"),
        source_node_id=node_id,
        content_hash="a" * 64,
    )
    envelope._update_content_hash()
    signature = ModelNodeSignature(
        node_id=node_id,
        signature="c2ln",
        key_id=uuid4(),
        envelope_state_hash=envelope.content_hash,
        operation=EnumNodeOperation.SOURCE,
        hop_index=0,
    )
    return envelope, signature


@pytest.mark.unit
def test_add_signature_emits_closed_event_with_canonical_key_id() -> None:
    """The production add path records exactly one complete audit event."""
    envelope, signature = _envelope_and_signature()

    envelope.add_signature(signature)

    assert len(envelope.signature_chain.signatures) == 1
    assert len(envelope.security_events) == 1
    assert envelope.signature_chain.content_hash == envelope.content_hash
    event = envelope.security_events[0]
    assert event.key_id == signature.key_id
    assert event.node_id == signature.node_id
    assert event.algorithm == signature.signature_algorithm.value


@pytest.mark.unit
def test_add_signature_keeps_chain_and_events_unchanged_when_chain_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A chain failure cannot leave a signature without its audit event."""
    envelope, signature = _envelope_and_signature()

    def reject_transition(
        self: ModelSignatureChain,
        candidate: ModelNodeSignature,
        validate_chain: bool = True,
    ) -> bool:
        del self, candidate, validate_chain
        return False

    monkeypatch.setattr(ModelSignatureChain, "add_signature", reject_transition)

    envelope.add_signature(signature)

    assert envelope.signature_chain.signatures == []
    assert envelope.security_events == []


@pytest.mark.unit
def test_add_signature_keeps_chain_and_events_unchanged_when_chain_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception in the isolated transition cannot mutate the envelope."""
    envelope, signature = _envelope_and_signature()
    original_chain = envelope.signature_chain
    original_content_hash = original_chain.content_hash

    def fail_transition(
        self: ModelSignatureChain,
        candidate: ModelNodeSignature,
        validate_chain: bool = True,
    ) -> bool:
        del validate_chain
        self.content_hash = "f" * 64
        self.signatures.append(candidate)
        raise ModelOnexError(message="chain failure")

    monkeypatch.setattr(ModelSignatureChain, "add_signature", fail_transition)

    with pytest.raises(ModelOnexError, match="chain failure"):
        envelope.add_signature(signature)

    assert envelope.signature_chain is original_chain
    assert envelope.signature_chain.content_hash == original_content_hash
    assert envelope.signature_chain.signatures == []
    assert envelope.security_events == []


@pytest.mark.unit
def test_add_signature_rejects_wrong_state_hash_atomically() -> None:
    """A stale production signature cannot mutate the envelope or audit trail."""
    envelope, signature = _envelope_and_signature()
    stale_signature = signature.model_copy(
        update={"envelope_state_hash": "b" * 64},
    )
    original_chain = envelope.signature_chain
    original_content_hash = original_chain.content_hash
    original_signatures = list(original_chain.signatures)

    with pytest.raises(ModelOnexError, match="envelope state hash mismatch"):
        envelope.add_signature(stale_signature)

    assert envelope.signature_chain is original_chain
    assert envelope.signature_chain.content_hash == original_content_hash
    assert envelope.signature_chain.signatures == original_signatures
    assert envelope.security_events == []


@pytest.mark.unit
def test_log_security_event_rejects_undeclared_signature_key_id() -> None:
    """Unknown audit wire keys fail closed and never append an event."""
    envelope, _ = _envelope_and_signature()

    with pytest.raises(ValidationError) as exc_info:
        envelope.log_security_event(
            event_type=EnumSecurityEventType.TOOL_ACCESS,
            signature_key_id=UUID(int=1),
        )

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
    assert envelope.security_events == []
