# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire Schema Contract Model.

Pydantic model for loading and validating wire schema contract YAML files.
Wire schema contracts are the single source of truth for cross-repo Kafka
topic field schemas — producer code, consumer models, and CI gates all
derive from these contracts.

Ticket: OMN-7357
Precedent: omnibase_infra routing_decision_v1.yaml (OMN-3425)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.governance.model_wire_ci_gate import ModelWireCiGate
from omnibase_core.models.governance.model_wire_collapsed_field import (
    ModelWireCollapsedField,
)
from omnibase_core.models.governance.model_wire_consumer import ModelWireConsumer
from omnibase_core.models.governance.model_wire_optional_field import (
    ModelWireOptionalField,
)
from omnibase_core.models.governance.model_wire_producer import ModelWireProducer
from omnibase_core.models.governance.model_wire_renamed_field import (
    ModelWireRenamedField,
)
from omnibase_core.models.governance.model_wire_required_field import (
    ModelWireRequiredField,
)


class ModelWireSchemaContract(BaseModel):
    """Wire schema contract for a Kafka topic.

    This model validates the YAML structure of wire schema contracts.
    It is the Pydantic representation of the canonical wire schema
    contract spec defined in OMN-7357.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(..., description="Kafka topic name")
    schema_version: str = Field(
        ..., description="Schema version (semver)"
    )  # string-version-ok: wire type serialized to YAML/JSON at contract boundary
    ticket: str = Field(default="", description="Originating ticket")
    description: str = Field(default="", description="Contract description")

    producer: ModelWireProducer = Field(..., description="Producer declaration")
    consumer: ModelWireConsumer = Field(..., description="Consumer declaration")

    required_fields: list[ModelWireRequiredField] = Field(
        ..., description="Required fields the producer MUST emit"
    )
    optional_fields: list[ModelWireOptionalField] = Field(
        default_factory=list, description="Optional fields the producer MAY emit"
    )
    renamed_fields: list[ModelWireRenamedField] = Field(
        default_factory=list, description="Fields with active rename shims"
    )
    collapsed_fields: list[ModelWireCollapsedField] = Field(
        default_factory=list, description="Fields collapsed into other fields"
    )
    ci_gate: ModelWireCiGate | None = Field(
        default=None, description="CI gate test declaration"
    )

    @model_validator(mode="after")
    def _no_duplicate_field_names(self) -> ModelWireSchemaContract:
        """Reject contracts with duplicate field names within required or optional."""
        required_names = [f.name for f in self.required_fields]
        optional_names = [f.name for f in self.optional_fields]

        req_dupes = [n for n in required_names if required_names.count(n) > 1]
        if req_dupes:
            msg = f"Duplicate required_fields names: {sorted(set(req_dupes))}"
            raise ValueError(msg)

        opt_dupes = [n for n in optional_names if optional_names.count(n) > 1]
        if opt_dupes:
            msg = f"Duplicate optional_fields names: {sorted(set(opt_dupes))}"
            raise ValueError(msg)

        overlap = set(required_names) & set(optional_names)
        if overlap:
            msg = f"Field names appear in both required and optional: {sorted(overlap)}"
            raise ValueError(msg)

        active_producer_names = [
            r.producer_name for r in self.renamed_fields if r.shim_status == "active"
        ]
        active_dupes = [
            n for n in active_producer_names if active_producer_names.count(n) > 1
        ]
        if active_dupes:
            msg = (
                "Duplicate active renamed_fields producer_name values: "
                f"{sorted(set(active_dupes))}"
            )
            raise ValueError(msg)

        return self

    @property
    def all_field_names(self) -> set[str]:
        """Return all declared field names (required + optional)."""
        return {f.name for f in self.required_fields} | {
            f.name for f in self.optional_fields
        }

    @property
    def required_field_names(self) -> set[str]:
        """Return required field names."""
        return {f.name for f in self.required_fields}

    @property
    def optional_field_names(self) -> set[str]:
        """Return optional field names."""
        return {f.name for f in self.optional_fields}

    @property
    def active_renamed_fields(self) -> dict[str, str]:
        """Return mapping of producer_name -> canonical_name for active shims."""
        return {
            r.producer_name: r.canonical_name
            for r in self.renamed_fields
            if r.shim_status == "active"
        }
