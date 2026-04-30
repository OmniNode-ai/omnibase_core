# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Address model for targeting concrete ONEX runtime instances."""

from __future__ import annotations

import re
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.types import JsonType

RuntimeIngressTransport = Literal["unix_socket", "http"]

_RUNTIME_ADDRESS_PATTERN = re.compile(
    r"^runtime://(?P<box>[A-Za-z0-9._-]+)/(?P<runtime>[A-Za-z0-9._-]+)$"
)
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class ModelRuntimeAddress(BaseModel):
    """Concrete address for a runtime that can receive routed work."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    address: str = Field(
        ...,
        min_length=1,
        description="Stable runtime address, for example runtime://box/runtime-id.",
    )
    runtime_id: str = Field(  # string-id-ok: human-readable runtime address component, not a database UUID
        ...,
        min_length=1,
        description="Runtime identity used by the gateway/signing layer.",
    )
    box_id: str = Field(  # string-id-ok: human-readable host or box name
        ...,
        min_length=1,
        description="Host or box identity that owns this runtime instance.",
    )
    environment: str = Field(
        ...,
        min_length=1,
        description="Routing environment or realm for this runtime.",
    )
    ingress_transport: RuntimeIngressTransport = Field(
        ...,
        description="Transport used to submit local runtime requests.",
    )
    ingress_address: str = Field(
        ...,
        min_length=1,
        description="Unix socket path or HTTP URL for runtime ingress.",
    )
    bus_id: str = Field(  # string-id-ok: named event-bus identity, not a database UUID
        ...,
        min_length=1,
        description="Event-bus identity used by this runtime.",
    )
    consumer_group_prefix: str = Field(
        ...,
        min_length=1,
        description="Prefix for runtime-owned consumer groups.",
    )
    capabilities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Capabilities this runtime can execute or broker.",
    )
    compose_project: str | None = Field(
        default=None,
        min_length=1,
        description="Optional Docker Compose project name for containerized runtimes.",
    )
    state_root: str | None = Field(
        default=None,
        min_length=1,
        description="Optional runtime state root path.",
    )
    metadata: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Small serializable metadata for operators and routers.",
    )

    @field_validator(
        "runtime_id",
        "box_id",
        "environment",
        "bus_id",
        "consumer_group_prefix",
        "compose_project",
        mode="after",
    )
    @classmethod
    def _validate_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("runtime address token must be non-empty")
        if not _TOKEN_PATTERN.fullmatch(normalized):
            raise ValueError(
                "runtime address token must contain only letters, numbers, '.', '_', '-', or ':'"
            )
        return normalized

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        normalized = value.strip()
        if not _RUNTIME_ADDRESS_PATTERN.fullmatch(normalized):
            raise ValueError("address must match runtime://<box_id>/<runtime_id>")
        return normalized

    @field_validator("capabilities", mode="before")
    @classmethod
    def _coerce_capabilities(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("capabilities")
    @classmethod
    def _validate_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            capability = item.strip()
            if not capability:
                raise ValueError("capability names must be non-empty")
            if not _TOKEN_PATTERN.fullmatch(capability):
                raise ValueError(f"invalid capability name: {capability}")
            if capability in seen:
                raise ValueError(f"duplicate capability name: {capability}")
            seen.add(capability)
            normalized.append(capability)
        return tuple(normalized)

    @field_validator("ingress_address")
    @classmethod
    def _validate_ingress_address(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ingress_address must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _validate_address_alignment(self) -> Self:
        match = _RUNTIME_ADDRESS_PATTERN.fullmatch(self.address)
        if match is None:
            raise ValueError("address must match runtime://<box_id>/<runtime_id>")
        if match.group("box") != self.box_id:
            raise ValueError("address box_id must match box_id field")
        if match.group("runtime") != self.runtime_id:
            raise ValueError("address runtime_id must match runtime_id field")

        if self.ingress_transport == "unix_socket":
            if not self.ingress_address.startswith("/"):
                raise ValueError("unix_socket ingress_address must be an absolute path")
        elif self.ingress_transport == "http":
            parsed = urlparse(self.ingress_address)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("http ingress_address must be an http(s) URL")
        return self

    def has_capabilities(self, required: tuple[str, ...]) -> bool:
        """Return whether this runtime satisfies all required capabilities."""
        return set(required).issubset(self.capabilities)


__all__ = ["ModelRuntimeAddress", "RuntimeIngressTransport"]
