# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The one result a delegation dispatch port returns (OMN-19838)."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)
from omnibase_core.enums.enum_quality_score_comparison import (
    EnumQualityScoreComparison,
)
from omnibase_core.models.delegation.wire.model_delegation_contract_evidence import (
    ModelDelegationContractEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_output_refusal import (
    ModelDelegationOutputRefusal,
)

# Pairs of names that providers have used for the same fact, as
# (canonical field, older name). A text pair keeps a non-empty canonical value
# and otherwise takes the older name's value, which is how the consumer handler
# reads them (``a or b``).
_TEXT_NAME_PAIRS: tuple[tuple[str, str], ...] = (
    ("error_message", "failure_reason"),
    ("model_name", "model_used"),
    ("provider", "delegated_to"),
    ("model_cloud_baseline", "baseline_model"),
)

# Pairs read by presence (``get(a, get(b))``): a present canonical value wins
# even when it is falsy.
_PRESENCE_NAME_PAIRS: tuple[tuple[str, str], ...] = (
    ("quality_gate_passed", "quality_passed"),
    ("input_tokens", "prompt_tokens"),
    ("output_tokens", "completion_tokens"),
    ("delegation_latency_ms", "latency_ms"),
)


class ModelDelegationDispatchResult(BaseModel):
    """The terminal facts of one delegation dispatch, as one typed value.

    It replaces the untyped mapping ``dispatch(...)`` returns. The field set is
    the union of the keys the consumer handler reads, with one canonical field
    for each pair of names providers have used for the same fact:

    - ``failure_reason`` -> ``error_message``
    - ``model_used`` -> ``model_name``
    - ``delegated_to`` -> ``provider``
    - ``baseline_model`` -> ``model_cloud_baseline``
    - ``quality_passed`` -> ``quality_gate_passed``
    - ``prompt_tokens`` / ``completion_tokens`` -> ``input_tokens`` /
      ``output_tokens``
    - ``latency_ms`` -> ``delegation_latency_ms``

    A payload may carry the older name; validation folds it into the canonical
    field with the precedence the handler applies, and only the canonical name
    is ever emitted. Any other unknown key is rejected, so a new fact is added
    here as a field rather than passed through unread.

    ``None`` on an optional field means the port did not report the fact, which
    is different from a reported zero. ``secret_source``, ``credential_refusal``
    and ``credential_withheld`` carry the provider's value unparsed, because
    their typed forms are defined above core; the consumer parses them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: str = Field(
        default="completed",
        description=(
            "Terminal status: completed, failed or timeout. The consumer treats any "
            "other value as a failure naming the unknown status."
        ),
    )
    content: str = Field(default="", description="The delegated response text.")
    error_message: str = Field(
        default="", description="Why the delegation failed; empty on success."
    )
    quality_gate_passed: bool = Field(
        default=False, description="Whether the quality gate accepted the response."
    )
    quality_gates_failed: tuple[str, ...] = Field(
        default=(), description="Names of the quality gates that refused."
    )
    quality_score: float | None = Field(
        default=None, description="Quality score of the accepted or last attempt."
    )
    required_quality_bar: float | None = Field(
        default=None, description="Quality bar the score was compared against."
    )
    score_vs_required_bar: EnumQualityScoreComparison | None = Field(
        default=None, description="Where the score sits against the bar."
    )
    failed_acceptance_criteria: tuple[str, ...] = Field(
        default=(), description="Acceptance criteria the response failed."
    )
    terminal_failure_cause: EnumDelegationTerminalFailureCause | None = Field(
        default=None, description="Typed terminal failure cause, when one was named."
    )
    provider: str = Field(
        default="", description="Provider identity that served the call."
    )
    model_name: str = Field(default="", description="Model that served the call.")
    model_cloud_baseline: str | None = Field(
        default=None, description="Premium baseline model for the counterfactual."
    )
    pricing_manifest_version: int | None = Field(
        default=None, description="Pricing manifest version the costs were read at."
    )
    secret_source: str | None = Field(
        default=None, description="Surface that resolved the credential, unparsed."
    )
    secret_ref: str | None = Field(
        default=None, description="Reference of the credential that was resolved."
    )
    response_contract_evidence: ModelDelegationContractEvidence | None = Field(
        default=None, description="Evidence about the declared response contract."
    )
    output_refusal: ModelDelegationOutputRefusal | None = Field(
        default=None, description="Why the output was refused, when it was."
    )
    preamble_chars: int | None = Field(
        default=None, ge=0, description="Characters of reasoning preamble removed."
    )
    credential_refusal: dict[str, object] | None = Field(
        default=None, description="Local credential refusal payload, unparsed."
    )
    credential_withheld: dict[str, object] | None = Field(
        default=None, description="Withheld-rung credential payload, unparsed."
    )
    input_tokens: int = Field(
        default=0, ge=0, description="Input tokens of the answering call."
    )
    output_tokens: int = Field(
        default=0, ge=0, description="Output tokens of the answering call."
    )
    total_tokens: int = Field(default=0, ge=0, description="Total tokens.")
    cumulative_input_tokens: int | None = Field(
        default=None, ge=0, description="Input tokens summed over every attempt."
    )
    cumulative_output_tokens: int | None = Field(
        default=None, ge=0, description="Output tokens summed over every attempt."
    )
    tokens_to_compliance: int = Field(
        default=0, ge=0, description="Tokens spent until the response complied."
    )
    compliance_attempts: int | None = Field(
        default=None, ge=0, description="Attempts made until the response complied."
    )
    cost_usd: float = Field(default=0.0, ge=0.0, description="Metered cost in USD.")
    cumulative_attempt_cost: float | None = Field(
        default=None, ge=0.0, description="Metered cost summed over every attempt."
    )
    final_attempt_cost: float | None = Field(
        default=None, ge=0.0, description="Metered cost of the final attempt."
    )
    cost_savings_usd: float | None = Field(
        default=None, description="Savings against the premium baseline, in USD."
    )
    delegation_latency_ms: int = Field(
        default=0, ge=0, description="Delegation latency in milliseconds."
    )
    escalation_count: int = Field(
        default=0, ge=0, description="Tier escalations taken."
    )
    attempts_count: int | None = Field(
        default=None,
        ge=0,
        description="Provider calls made; authoritative over the attempt records.",
    )
    attempts: tuple[dict[str, object], ...] | None = Field(
        default=None,
        description=(
            "Per-attempt records from the port. When present they win over "
            "escalation_history."
        ),
    )
    escalation_history: tuple[dict[str, object], ...] = Field(
        default=(),
        description="Serialized escalation history from a bus terminal.",
    )

    @model_validator(mode="before")
    @classmethod
    def _fold_older_names(cls, data: object) -> object:
        if not isinstance(data, Mapping):
            return data
        folded: dict[str, object] = {str(key): value for key, value in data.items()}
        failure_reason = folded.get("failure_reason")
        if "quality_gates_failed" not in folded and failure_reason:
            folded["quality_gates_failed"] = failure_reason
        for canonical, older in _TEXT_NAME_PAIRS:
            if older not in folded:
                continue
            older_value = folded.pop(older)
            if older_value and not folded.get(canonical):
                folded[canonical] = older_value
        for canonical, older in _PRESENCE_NAME_PAIRS:
            if older not in folded:
                continue
            older_value = folded.pop(older)
            folded.setdefault(canonical, older_value)
        return folded

    @field_validator("quality_gates_failed", mode="before")
    @classmethod
    def _one_gate_name_is_a_one_item_tuple(cls, value: object) -> object:
        if isinstance(value, str):
            return (value,) if value else ()
        return value


__all__ = ["ModelDelegationDispatchResult"]
