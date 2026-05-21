# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strongly typed LLM endpoint configuration for contract config blocks (OMN-11430)."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ModelLlmEndpointConfig(BaseModel):
    """LLM endpoint URLs and model names declared in contract config."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    coder_url: str | None = Field(
        default=None, description="Primary coder LLM endpoint URL"
    )
    coder_fast_url: str | None = Field(
        default=None, description="Fast coder LLM endpoint URL"
    )
    coder_model_name: str | None = Field(
        default=None, description="Primary coder model name"
    )
    coder_fast_model_name: str | None = Field(
        default=None, description="Fast coder model name"
    )
    deepseek_r1_url: str | None = Field(
        default=None, description="DeepSeek R1 endpoint URL"
    )
    glm_url: str | None = Field(default=None, description="GLM endpoint URL")
    glm_api_key: SecretStr | None = Field(default=None, description="GLM API key")
    gemini_api_key: SecretStr | None = Field(default=None, description="Gemini API key")
    openai_api_key: SecretStr | None = Field(default=None, description="OpenAI API key")
