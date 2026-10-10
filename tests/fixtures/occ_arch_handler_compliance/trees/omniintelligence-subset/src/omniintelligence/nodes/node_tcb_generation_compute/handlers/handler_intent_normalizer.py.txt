# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent normalization for TCB generation."""

from __future__ import annotations

from omnibase_core.models.ticket.model_ticket_context_bundle import (
    ModelTCBNormalizedIntent,
)

RISK_KEYWORDS: dict[str, list[str]] = {
    "migration": ["migrat", "alembic", "schema change", "add column", "rename column"],
    "security": ["auth", "permission", "token", "credential", "secret", "encrypt"],
    "concurrency": ["async", "race condition", "lock", "deadlock", "concurrent"],
    "perf": ["performance", "slow", "optimize", "cache", "index", "bottleneck"],
    "integration": [
        "kafka",
        "topic",
        "consumer",
        "producer",
        "api contract",
        "endpoint",
    ],
}

CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    "routing": ["routing", "route", "dispatch"],
    "auth": ["auth", "authentication", "authorization", "permission"],
    "ledger": ["ledger", "audit", "log", "history"],
    "schema": ["schema", "model", "pydantic", "contract", "validator"],
    "embedding": ["embedding", "vector", "qdrant", "semantic"],
    "pattern": ["pattern", "learning", "feedback"],
}


def normalize_intent(
    raw: str,
    repo_manifest: dict[str, list[str]],
) -> ModelTCBNormalizedIntent:
    """Normalize raw intent text into structured tags.

    Args:
        raw: Raw ticket title + description text
        repo_manifest: Map of repo_name to list of keyword signals

    Returns:
        ModelTCBNormalizedIntent with repos, modules, capability_tags, risk_tags
    """
    text_lower = raw.lower()

    # Repo detection: check which repo's keywords appear in the text
    repos: list[str] = []
    modules: list[str] = []
    for repo, keywords in repo_manifest.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if repo not in repos:
                    repos.append(repo)
                if kw not in modules:
                    modules.append(kw)
                break

    # Explicit repo name mentions (e.g. "in omnibase_core")
    for repo in repo_manifest:
        if repo in text_lower and repo not in repos:
            repos.append(repo)

    # Risk tags
    risk_tags: list[str] = []
    for tag, signals in RISK_KEYWORDS.items():
        if any(s in text_lower for s in signals):
            risk_tags.append(tag)

    # Capability tags
    capability_tags: list[str] = []
    for cap, signals in CAPABILITY_KEYWORDS.items():
        if any(s in text_lower for s in signals):
            capability_tags.append(cap)

    return ModelTCBNormalizedIntent(
        repos=repos,
        modules=modules,
        capability_tags=capability_tags,
        risk_tags=risk_tags,
    )
