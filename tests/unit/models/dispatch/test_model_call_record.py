# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for dispatch model-call records and cost provenance."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.cost import EnumUsageSource
from omnibase_core.models.cost import ModelCostProvenance
from omnibase_core.models.dispatch import ModelCallRecord


@pytest.mark.unit
def test_model_call_record_accepts_valid_measured_cost_provenance() -> None:
    call = ModelCallRecord(
        provider="openai",
        model="gpt-5-mini",
        input_tokens=100,
        output_tokens=25,
        latency_ms=250,
        cost_dollars=0.01,
        cost_provenance=ModelCostProvenance(
            usage_source=EnumUsageSource.MEASURED,
            source_payload_hash="hash-1",
        ),
    )

    assert call.cost_provenance.usage_source == EnumUsageSource.MEASURED
    assert isinstance(call.cost_provenance.usage_source, EnumUsageSource)


@pytest.mark.unit
def test_model_call_record_is_frozen() -> None:
    call = ModelCallRecord(
        provider="openai",
        model="gpt-5-mini",
        input_tokens=0,
        output_tokens=0,
        latency_ms=0,
        cost_dollars=0,
        cost_provenance=ModelCostProvenance(usage_source=EnumUsageSource.UNKNOWN),
    )

    with pytest.raises(ValidationError):
        call.provider = "anthropic"


@pytest.mark.unit
def test_cost_provenance_enforces_estimated_required_and_null_fields() -> None:
    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.ESTIMATED,
            estimation_method=None,
        )

    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.ESTIMATED,
            estimation_method="pricing_table",
            source_payload_hash="not-allowed",
        )


@pytest.mark.unit
def test_cost_provenance_enforces_measured_required_and_null_fields() -> None:
    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.MEASURED,
            source_payload_hash=None,
        )

    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.MEASURED,
            estimation_method="not-allowed",
            source_payload_hash="hash-1",
        )


@pytest.mark.unit
def test_cost_provenance_enforces_unknown_null_fields() -> None:
    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.UNKNOWN,
            estimation_method="not-allowed",
        )

    with pytest.raises(ValidationError):
        ModelCostProvenance(
            usage_source=EnumUsageSource.UNKNOWN,
            source_payload_hash="not-allowed",
        )
