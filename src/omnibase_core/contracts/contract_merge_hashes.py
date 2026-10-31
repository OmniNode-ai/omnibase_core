# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic resolver configuration and effective contract hashes (OMN-21506)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef

__all__ = ["compute_resolver_config_hash", "compute_effective_contract_hash"]


def _canonical_json_sha256(payload: dict[str, object]) -> str:
    """Hash a payload using canonical JSON encoded as UTF-8."""
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def compute_resolver_config_hash(
    *,
    profile: str,
    profile_version: str,
    node_type: EnumNodeType,
    overlay_refs: Sequence[ModelOverlayRef],
) -> str:
    """Hash the resolver configuration, preserving overlay application order."""
    payload: dict[str, object] = {
        "profile": profile,
        "profile_version": profile_version,
        "node_type": node_type.value,
        "overlay_refs": [ref.model_dump(mode="json") for ref in overlay_refs],
    }
    return _canonical_json_sha256(payload)


def compute_effective_contract_hash(contract: ModelHandlerContract) -> str:
    """Hash the complete JSON representation of the effective contract."""
    return _canonical_json_sha256(contract.model_dump(mode="json"))
