# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The one request a delegation dispatch port accepts (OMN-19838)."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.delegation.wire.model_delegation_provenance import (
    ModelDelegationProvenance,
)
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    EnumQualityContractMode,
)


class ModelDelegationDispatchRequest(BaseModel):
    """Every argument of one delegation dispatch, as one typed value.

    It replaces the keyword arguments of ``dispatch(...)``: a port's single
    method is ``dispatch(request) -> ModelDelegationDispatchResult`` (see
    ``omnibase_core.protocols.runtime.ProtocolDelegationDispatchPort``). The
    field set is every argument the consumer handler sends, plus the provider's
    ``output_schema_key``.

    The identity (``prompt``, ``task_type``, ``correlation_id``) and the
    execution budget the handler resolved from the task class are required.
    Every other field is an option with a default, and a new dispatch option is
    added here as a defaulted field, so a port that does not act on it yet sees
    its default rather than an unexpected argument.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    prompt: str = Field(..., min_length=1, description="The prompt to delegate.")
    task_type: str = Field(
        ..., min_length=1, description="Task class that selects routing and budget."
    )
    correlation_id: UUID = Field(
        ..., description="Correlation id of the delegation, end to end."
    )
    execution_timeout_seconds: int = Field(
        ...,
        gt=0,
        description="Execution budget resolved from the task class, in seconds.",
    )
    terminal_delivery_margin_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "Interval after the execution budget that the port's terminal waiter "
            "allows for the terminal to be delivered, in seconds."
        ),
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Explicit output-token budget. None lets the port resolve it from the "
            "selected backend's ceiling in the routing contract."
        ),
    )
    source_file_path: str | None = Field(
        default=None, description="Source file the prompt concerns, when known."
    )
    # string-id-ok: caller session ids are opaque strings, not UUIDs
    source_session_id: str | None = Field(
        default=None, description="Caller session id, when known."
    )
    wait: bool = Field(
        default=True, description="Wait for the terminal result synchronously."
    )
    quality_contract_mode: EnumQualityContractMode = Field(
        default="extend_task_class",
        description=(
            "Whether acceptance_criteria extend or replace the task class's "
            "quality contract."
        ),
    )
    acceptance_criteria: tuple[str, ...] = Field(
        default=(), description="Caller-declared acceptance criteria."
    )
    # string-id-ok: tenant_id is a named tenant identifier, not a UUID
    tenant_id: str | None = Field(
        default=None,
        description="Verified tenant id stamped at ingress, never self-reported.",
    )
    provenance: ModelDelegationProvenance | None = Field(
        default=None,
        description=(
            "Typed provenance carried unchanged to the terminal. None is "
            "unclassified, never synthetic."
        ),
    )
    # string-id-ok: backend references are named contract slugs, not UUIDs
    backend_id: str | None = Field(
        default=None,
        description="Backend pin. None keeps the cheapest-first tier resolution.",
    )
    no_escalation: bool = Field(
        default=False,
        description=(
            "One provider call, no retry and no tier escalation. True requires a "
            "backend_id pin."
        ),
    )
    response_contract: dict[str, object] | None = Field(
        default=None,
        description=(
            "Caller-declared JSON Schema for the response. None keeps the task "
            "class's declared default, if any."
        ),
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt. None keeps the task class's default.",
    )
    temperature: float | None = Field(
        default=None,
        description="Sampling temperature. None keeps the effect layer's default.",
    )
    response_format: dict[str, object] | None = Field(
        default=None,
        description=(
            "Chat-completions response_format. None sends no response_format key."
        ),
    )
    output_schema_key: str | None = Field(
        default=None,
        description="Registered output schema key the provider validates against.",
    )

    @model_validator(mode="after")
    def _no_escalation_requires_a_backend_pin(self) -> Self:
        if self.no_escalation and self.backend_id is None:
            msg = "no_escalation requires backend_id"
            raise ValueError(msg)
        return self


__all__ = ["ModelDelegationDispatchRequest"]
