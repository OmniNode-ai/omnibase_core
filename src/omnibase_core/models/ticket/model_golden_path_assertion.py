# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoldenPathAssertion — field-level assertion for golden path tests.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_golden_path.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any

_MAX_STRING_LENGTH = 10000


@allow_dict_str_any(
    reason=(
        "Golden path assertion value is genuinely polymorphic: the field under "
        "test may hold str, int, float, bool, list, dict, or None depending on "
        "the node output schema. A typed model is not possible without runtime "
        "introspection of each node's output schema."
    )
)
class ModelGoldenPathAssertion(BaseModel):
    """A single assertion on an output event field.

    Specifies a field path, comparison operator, and expected value.
    Assertions are evaluated against the output event produced by running
    the golden path test.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(
        ...,
        description=(
            "Dot-separated field path on the output event "
            "(e.g., 'status' or 'data.result')"
        ),
        max_length=_MAX_STRING_LENGTH,
    )
    op: Literal["eq", "neq", "gte", "lte", "in", "contains"] = Field(
        ...,
        description="Comparison operator: eq | neq | gte | lte | in | contains",
    )
    # dict-str-any-ok: assertion value is polymorphic across all node output schemas
    value: str | int | float | bool | list[Any] | dict[str, Any] | None = Field(
        ...,
        description="Expected value to compare against",
    )


__all__ = ["ModelGoldenPathAssertion"]
