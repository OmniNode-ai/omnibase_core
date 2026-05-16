# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelGenerationAttempt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    attempt_number: int
    provider: str
    model_id: str  # string-id-ok: human-readable model label (e.g. "gemini-flash")
    endpoint_class: str
    token_usage_input: int
    token_usage_output: int
    latency_inference_ms: int
    contract_passed: bool
    validation_errors: list[str]
