# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.primitives.model_semver import ModelSemVer

SUPPORTED_OVERLAY_VERSIONS: frozenset[str] = frozenset({"1.0.0"})

_SECRET_KEY_PATTERN = re.compile(  # NOSONAR
    "|".join(["PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL"]),  # NOSONAR
    re.IGNORECASE,
)


def _redact_section(section: object) -> None:
    if not isinstance(section, dict):
        return
    for sub_key, sub_val in section.items():
        if isinstance(sub_val, dict):
            for k in sub_val:
                if _SECRET_KEY_PATTERN.search(k):
                    sub_val[k] = "***REDACTED***"
        elif isinstance(sub_val, str) and _SECRET_KEY_PATTERN.search(sub_key):
            section[sub_key] = "***REDACTED***"


class ModelOverlayFile(BaseModel):
    """Frozen schema for overlay YAML files. Validated at model level so invalid overlays are rejected regardless of construction path."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay_version: ModelSemVer = Field(...)
    environment: str = Field(..., min_length=1)
    scope: EnumOverlayScope = Field(...)
    transports: dict[str, dict[str, str]] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)
    services: dict[str, dict[str, str]] = Field(default_factory=dict)
    llm: dict[str, dict[str, str]] = Field(default_factory=dict)

    @field_validator("overlay_version", mode="before")
    @classmethod
    def _validate_overlay_version(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v not in SUPPORTED_OVERLAY_VERSIONS:
                msg = (
                    f"overlay_version '{v}' not in supported set: "
                    f"{sorted(SUPPORTED_OVERLAY_VERSIONS)}"
                )
                raise ValueError(msg)
            return ModelSemVer.parse(v)
        if isinstance(v, dict):
            parsed = ModelSemVer.model_validate(v)
            if str(parsed) not in SUPPORTED_OVERLAY_VERSIONS:
                msg = (
                    f"overlay_version '{parsed}' not in supported set: "
                    f"{sorted(SUPPORTED_OVERLAY_VERSIONS)}"
                )
                raise ValueError(msg)
            return parsed
        return v

    def content_hash(self) -> str:
        """SHA-256 of JSON-serialized model with keys sorted for deterministic output across insertion orders."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"

    def all_env_pairs(self) -> dict[str, str]:
        """Flatten all sections into a single env-pair dict. Raises ValueError on duplicate keys with conflicting values; identical duplicate values are accepted."""
        pairs: dict[str, str] = {}
        sources: list[tuple[str, dict[str, str]]] = []
        for section_name, transport_vals in self.transports.items():
            sources.append((f"transports.{section_name}", transport_vals))
        sources.append(("secrets", self.secrets))
        for section_name, svc_vals in self.services.items():
            sources.append((f"services.{section_name}", svc_vals))
        for section_name, llm_vals in self.llm.items():
            sources.append((f"llm.{section_name}", llm_vals))

        for source_label, kv in sources:
            for key, value in kv.items():
                if key in pairs and pairs[key] != value:
                    raise ValueError(  # error-ok: boundary ValueError for duplicate key in public API
                        f"Key '{key}' conflict: '{pairs[key]}' vs {source_label}='{value}'"
                    )
                pairs[key] = value
        return pairs

    def redacted_dump(self) -> dict[str, object]:
        """Return model_dump with PASSWORD/SECRET/TOKEN/KEY/CREDENTIAL-named values replaced by '***REDACTED***'."""
        data = self.model_dump(mode="json")
        for section_key in ("transports", "secrets", "services", "llm"):
            _redact_section(data.get(section_key, {}))
        return data


__all__ = ["ModelOverlayFile", "SUPPORTED_OVERLAY_VERSIONS"]
