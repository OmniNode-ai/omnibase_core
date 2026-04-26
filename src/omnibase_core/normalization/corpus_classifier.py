# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Corpus classifier — path-based bucket assignment with secondary shape signals.

Maps a contract YAML file path to an ``EnumContractBucket``. Path classification
is primary; raw-dict shape inspection (when ``raw`` is supplied) acts as a
secondary signal that adjusts ``confidence`` and appends ``reasons`` but never
overrides the path-derived bucket.

OMN-9760, parent OMN-9757.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.models.contracts.model_corpus_classification import (
    ModelCorpusClassification,
)


def classify_contract_path(
    path: Path,
    raw: dict[str, object] | None = None,
) -> ModelCorpusClassification:
    """Classify a contract YAML file by its path with optional shape signals.

    Args:
        path: Filesystem path to a contract YAML (does not need to exist on disk).
        raw: Optional already-loaded raw dict to enable secondary shape signals.

    Returns:
        ModelCorpusClassification with bucket, requires_validation flag,
        always-non-empty ``reasons`` list, and optional ``confidence`` score
        when the classification is ambiguous.
    """
    parts = path.parts
    path_str = path.as_posix()
    raw_dict: dict[str, object] = raw or {}
    raw_node_type_value = raw_dict.get("node_type")
    raw_node_type: str | None = (
        raw_node_type_value if isinstance(raw_node_type_value, str) else None
    )
    reasons: list[str] = []
    confidence: float | None = None

    if "/integrations/" in path_str:
        bucket = EnumContractBucket.INTEGRATION_CONTRACT
        reasons.append("matched */integrations/* glob")
    elif "nodes" not in parts:
        bucket = EnumContractBucket.PACKAGE_CONTRACT
        reasons.append("no 'nodes' segment in path")
    else:
        nodes_idx = max(i for i, p in enumerate(parts) if p == "nodes")
        after_nodes = parts[nodes_idx + 1 :]
        if len(after_nodes) == 2 and after_nodes[-1] == "contract.yaml":
            bucket = EnumContractBucket.NODE_ROOT_CONTRACT
            reasons.append("matched */nodes/<name>/contract.yaml glob")
            if "node_type" in raw_dict:
                reasons.append("shape contains node_type field (confirms node_root)")
            elif raw_dict:
                reasons.append(
                    "shape missing node_type field (path match, shape mismatch)"
                )
                confidence = 0.7
        elif len(after_nodes) >= 2 and "handlers" in after_nodes:
            bucket = EnumContractBucket.HANDLER_CONTRACT
            reasons.append("matched */nodes/*/handlers/* glob")
            handler_block = raw_dict.get("handler")
            if isinstance(handler_block, dict) and "class" in handler_block:
                reasons.append(
                    "shape contains handler.class block (confirms handler_contract)"
                )
        else:
            bucket = EnumContractBucket.UNKNOWN
            reasons.append("no glob matched under nodes/ hierarchy")
            confidence = 0.3

    if not reasons:
        bucket = EnumContractBucket.UNKNOWN
        reasons.append("no glob matched")
        confidence = 0.3

    requires_validation = bucket is EnumContractBucket.NODE_ROOT_CONTRACT

    return ModelCorpusClassification(
        path=path,
        bucket=bucket,
        raw_node_type=raw_node_type,
        requires_validation=requires_validation,
        reasons=reasons,
        confidence=confidence,
    )


__all__ = ["classify_contract_path"]
