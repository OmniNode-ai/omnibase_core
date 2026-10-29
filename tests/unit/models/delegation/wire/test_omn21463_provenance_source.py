# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21463: ingress adapter names are data; provenance validates identifiers."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire.model_delegation_provenance import (
    ModelDelegationProvenance,
)


@pytest.mark.unit
def test_source_accepts_an_adapter_outside_the_old_closed_vocabulary() -> None:
    provenance = ModelDelegationProvenance(source="registered-adapter")

    assert provenance.source == "registered-adapter"
    assert ModelDelegationProvenance.model_validate_json(
        provenance.model_dump_json()
    ) == (provenance)


@pytest.mark.unit
@pytest.mark.parametrize("source", ["", " ", "\t", " adapter", "adapter ", "adapter\n"])
def test_source_rejects_blank_or_padded_identifiers(source: str) -> None:
    with pytest.raises(ValidationError, match="nonblank and unpadded"):
        ModelDelegationProvenance(source=source)
