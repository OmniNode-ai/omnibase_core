# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic UUID boundary regressions for signature-chain hashing."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_signature_chain import ModelSignatureChain


def _chain_and_signature() -> tuple[ModelSignatureChain, ModelNodeSignature]:
    chain = ModelSignatureChain(
        chain_id=uuid4(),
        envelope_id=uuid4(),
        content_hash="a" * 64,
    )
    signature = ModelNodeSignature(
        node_id=uuid4(),
        signature="c2ln",
        timestamp=datetime.now(UTC),
        operation=EnumNodeOperation.SOURCE,
        key_id=uuid4(),
        hop_index=0,
        envelope_state_hash=chain.content_hash,
    )
    return chain, signature


@pytest.mark.unit
def test_add_signature_hashes_uuid_boundary_deterministically_without_coercing_models() -> (
    None
):
    """UUIDs cross only the JSON hashing boundary; typed model fields stay UUIDs."""
    first_chain, first_signature = _chain_and_signature()
    second_chain = ModelSignatureChain(
        chain_id=first_chain.chain_id,
        envelope_id=first_chain.envelope_id,
        content_hash=first_chain.content_hash,
    )
    second_signature = first_signature.model_copy(deep=True)

    assert first_chain.add_signature(first_signature) is True
    assert second_chain.add_signature(second_signature) is True

    assert first_chain.chain_hash == second_chain.chain_hash
    assert isinstance(first_chain.chain_id, UUID)
    assert isinstance(first_chain.envelope_id, UUID)
    assert isinstance(first_chain.signatures[0].node_id, UUID)


@pytest.mark.unit
def test_signature_chain_rejects_unknown_fields() -> None:
    """The chain is a closed wire contract: an unknown field is refused, not dropped."""
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelSignatureChain.model_validate(
            {
                "chain_id": str(uuid4()),
                "envelope_id": str(uuid4()),
                "content_hash": "a" * 64,
                "unexpected_field": "dropped silently before OMN-17711",
            }
        )
