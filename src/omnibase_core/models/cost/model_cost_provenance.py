# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cost provenance model for measured, estimated, or unknown usage."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.cost import EnumUsageSource

if TYPE_CHECKING:
    from omnibase_core.models.dispatch.model_model_call_record import ModelCallRecord


class ModelCostProvenance(BaseModel):
    """Validated provenance for token and dollar cost attribution."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    usage_source: EnumUsageSource = Field(
        description="Whether usage/cost was measured, estimated, or unknown."
    )
    estimation_method: str | None = Field(
        default=None,
        description="Estimator name or method. Required only for estimated usage.",
    )
    source_payload_hash: str | None = Field(
        default=None,
        description="Stable payload hash. Required only for measured usage.",
    )

    @model_validator(mode="after")
    def validate_source_requirements(self) -> ModelCostProvenance:
        if self.usage_source == EnumUsageSource.MEASURED:
            if self.source_payload_hash is None:
                raise ValueError("source_payload_hash is required for measured usage")
            if self.estimation_method is not None:
                raise ValueError("estimation_method must be null for measured usage")
            return self

        if self.usage_source == EnumUsageSource.ESTIMATED:
            if self.estimation_method is None:
                raise ValueError("estimation_method is required for estimated usage")
            if self.source_payload_hash is not None:
                raise ValueError("source_payload_hash must be null for estimated usage")
            return self

        if self.estimation_method is not None:
            raise ValueError("estimation_method must be null for unknown usage")
        if self.source_payload_hash is not None:
            raise ValueError("source_payload_hash must be null for unknown usage")
        return self

    @classmethod
    def rollup(cls, calls: Sequence[ModelCallRecord]) -> ModelCostProvenance:
        """Roll up per-call provenance into dispatch-level cost provenance."""

        cost_bearing_calls = [
            call
            for call in calls
            if call.input_tokens > 0 or call.output_tokens > 0 or call.cost_dollars > 0
        ]
        if not cost_bearing_calls:
            return cls(usage_source=EnumUsageSource.UNKNOWN)

        if any(
            call.cost_provenance.usage_source == EnumUsageSource.ESTIMATED
            for call in cost_bearing_calls
        ):
            return cls(
                usage_source=EnumUsageSource.ESTIMATED,
                estimation_method="model_call_rollup",
            )

        if all(
            call.cost_provenance.usage_source == EnumUsageSource.MEASURED
            for call in cost_bearing_calls
        ):
            hashes = [
                call.cost_provenance.source_payload_hash
                for call in cost_bearing_calls
                if call.cost_provenance.source_payload_hash is not None
            ]
            source_payload_hash = hashlib.sha256(
                "\n".join(sorted(hashes)).encode("utf-8")
            ).hexdigest()
            return cls(
                usage_source=EnumUsageSource.MEASURED,
                source_payload_hash=source_payload_hash,
            )

        return cls(usage_source=EnumUsageSource.UNKNOWN)
