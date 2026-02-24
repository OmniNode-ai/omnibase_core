# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence item model for structured scoring input.

Only structured, ledger-backed evidence may be used as scoring input.
Free-form text, model confidence text, and unstructured chat logs are
explicitly disallowed.

Part of the objective functions and reward architecture (OMN-2537).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEvidenceItem"]

# Exhaustive typed source literals — free-text sources are explicitly NOT included
EvidenceSource = Literal[
    "test_output",
    "validator_result",
    "static_analysis",
    "build_warnings",
    "structured_review_tag",
    "cost_telemetry",
    "latency_telemetry",
]
"""Valid evidence sources for scoring input.

Allowed:
- test_output: pytest / test runner structured output
- validator_result: Gate execution records from contract validators
- static_analysis: mypy, ruff, lint structured output
- build_warnings: Structured compiler / build output
- structured_review_tag: Human review with typed classifications
- cost_telemetry: Ledger-backed cost events
- latency_telemetry: Measured execution durations

Disallowed (not representable in this type):
- Free-form review text (not structured, not replayable)
- Model confidence text (self-report, not falsifiable)
- Unstructured chat logs (cannot be fingerprinted or versioned)
"""


class ModelEvidenceItem(BaseModel):
    """A single structured evidence item for scoring input.

    Evidence items carry typed, structured data from specific sources.
    Free-text inputs are disallowed by the typed source literal — only
    the seven allowed source types can be represented.

    Attributes:
        item_id: Unique identifier for this evidence item within a bundle.
        source: The typed source of this evidence (disallows free-text inputs).
        key: The specific metric or check name within the source.
        value: The numeric value of this evidence item.
        unit: Optional unit description for the value (e.g., "ms", "count").
        ref: Optional reference to the originating ledger record or artifact.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    item_id: str = Field(  # string-id-ok: evidence item identifier within a bundle
        description="Unique identifier for this evidence item within the bundle"
    )
    source: EvidenceSource = Field(
        description=(
            "Typed evidence source — free-text inputs are structurally disallowed. "
            "Must be one of the seven allowed source types."
        )
    )
    key: str = Field(  # string-key-ok: metric or check name within the source
        description="Specific metric or check name within the source (e.g., 'tests_passed_count')"
    )
    value: float = Field(description="Numeric value of this evidence item")
    unit: str | None = Field(
        default=None,
        description="Optional unit description (e.g., 'ms', 'count', 'ratio')",
    )
    ref: str | None = Field(  # string-ref-ok: optional ledger record reference
        default=None,
        description="Optional reference to the originating ledger record or artifact",
    )
