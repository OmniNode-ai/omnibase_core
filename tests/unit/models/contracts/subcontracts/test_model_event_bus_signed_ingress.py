# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Signed ingress is a contract property, not a runtime topic guess."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

TOPIC = "onex.cmd.example.secure-read.v1"


def test_signed_ingress_must_name_an_existing_subscription() -> None:
    version = ModelSemVer(major=1, minor=0, patch=0)
    contract = ModelEventBusSubcontract(
        version=version,
        subscribe_topics=[TOPIC],
        signed_ingress_topics=[TOPIC],
    )
    assert contract.signed_ingress_topics == [TOPIC]

    with pytest.raises(ValidationError, match="signed_ingress_topics"):
        ModelEventBusSubcontract(
            version=version,
            subscribe_topics=[],
            signed_ingress_topics=[TOPIC],
        )
