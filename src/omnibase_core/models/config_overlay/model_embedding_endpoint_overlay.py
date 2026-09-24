# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``embedding.endpoint`` overlay document body (OMN-19391)."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelEmbeddingEndpointOverlay(BaseModel):
    """Where embeddings are computed, by which model, at which dimension.

    Carries a reference to the API key, never the key itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["embedding_endpoint.v1"] = Field(
        ..., description="Schema version tag."
    )
    endpoint_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Base URL of the embedding server.",
    )
    model_name: str = Field(
        ..., min_length=1, max_length=256, description="Model the server embeds with."
    )
    dimension: int = Field(..., gt=0, description="Embedding vector dimension.")
    api_key_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Reference to the API key in the secret store, when one is needed.",
    )

    @field_validator("endpoint_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("endpoint_url must be an absolute http or https URL")
        return value


__all__ = ["ModelEmbeddingEndpointOverlay"]
