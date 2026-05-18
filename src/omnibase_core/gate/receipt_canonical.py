# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical OmniGate receipt serialization helpers."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import cast

from omnibase_core.models.gate.model_omnigate_receipt import ModelOmniGateReceipt
from omnibase_core.types.type_json import JsonType


def _normalize_json(value: JsonType) -> JsonType:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_json(value[key]) for key in sorted(value)}
    return value


def canonical_receipt_payload(
    receipt: ModelOmniGateReceipt,
    *,
    exclude_signature: bool = True,
) -> bytes:
    """Return deterministic JSON bytes for OmniGate receipt signing/verification."""
    exclude = {"sigstore_bundle_json"} if exclude_signature else set()
    data = cast(
        JsonType,
        receipt.model_dump(mode="json", exclude=exclude, by_alias=True),
    )
    normalized = _normalize_json(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_receipt_schema_fingerprint() -> str:
    """Return a deterministic SHA-256 fingerprint for the receipt JSON schema."""
    schema = cast(JsonType, ModelOmniGateReceipt.model_json_schema())
    payload = json.dumps(
        _normalize_json(schema),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


__all__ = [
    "canonical_receipt_payload",
    "compute_receipt_schema_fingerprint",
]
