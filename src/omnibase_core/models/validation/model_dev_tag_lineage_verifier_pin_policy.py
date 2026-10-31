# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract parameters defining which workflow line pins the verifier to a release."""

from pydantic import BaseModel, ConfigDict, Field


class ModelDevTagLineageVerifierPinPolicy(BaseModel):
    """The pin line pattern and the workflow suffixes are rule-row data."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    pin_pattern: str = Field(min_length=1)
    workflow_suffixes: tuple[str, ...] = Field(min_length=1)
