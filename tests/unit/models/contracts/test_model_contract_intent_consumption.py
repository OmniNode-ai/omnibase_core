# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractIntentConsumption (contract ``intent_consumption:`` block, OMN-16451)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_intent_consumption import (
    ModelContractIntentConsumption,
)


@pytest.mark.unit
class TestModelContractIntentConsumption:
    def test_parses_routing_table(self) -> None:
        cfg = ModelContractIntentConsumption.model_validate(
            {
                "intent_routing_table": {
                    "postgres.upsert_registration": "node_registry_effect",
                    "postgres.update_registration": "node_registry_effect",
                }
            }
        )
        assert cfg.intent_routing_table["postgres.upsert_registration"] == (
            "node_registry_effect"
        )

    def test_routing_table_is_required(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelContractIntentConsumption.model_validate({})
        assert any(
            e["loc"] == ("intent_routing_table",) for e in exc_info.value.errors()
        )

    def test_empty_routing_table_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelContractIntentConsumption.model_validate({"intent_routing_table": {}})

    def test_rejects_unconsumed_subscribed_intents_key(self) -> None:
        """``subscribed_intents`` has no runtime reader, so it is not part of the schema."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractIntentConsumption.model_validate(
                {
                    "subscribed_intents": ["postgres.upsert_registration"],
                    "intent_routing_table": {
                        "postgres.upsert_registration": "node_registry_effect"
                    },
                }
            )
        assert any(
            e["type"] == "extra_forbidden" and e["loc"] == ("subscribed_intents",)
            for e in exc_info.value.errors()
        )
