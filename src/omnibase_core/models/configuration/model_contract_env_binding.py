# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed result of resolving one declared ``${env.VAR}`` contract reference."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractEnvBinding(BaseModel):
    """One declared contract-env reference, resolved.

    ``bound`` records whether the operator environment actually declares the
    variable. It is deliberately separate from ``value`` so a caller can tell
    "not configured" from "configured empty" — the distinction every override
    loop in this repo depends on, and the one a bare
    ``expand_contract_env_refs`` call cannot express, because an unset variable
    and an empty one both expand to ``""``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Variable name declared by the reference")
    reference: str = Field(description="The canonical ``${env.NAME}`` reference")
    bound: bool = Field(
        description="True when the operator environment declares the variable"
    )
    value: str | None = Field(
        default=None,
        description=(
            "Resolved value: the declared value when bound, otherwise the "
            "reference's inline default, otherwise None"
        ),
    )

    def is_configured(self) -> bool:
        """True when this binding resolved to a usable value."""
        return self.value is not None


__all__ = ["ModelContractEnvBinding"]
