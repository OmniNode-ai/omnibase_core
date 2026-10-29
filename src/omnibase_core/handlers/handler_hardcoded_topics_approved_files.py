# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Files the hardcoded-topics validator treats as source of truth (OMN-21503).

Moved out of ``validation/validator_hardcoded_topics.py`` unchanged, so the
validator file shrinks while it gains the host-list rule.
"""

from __future__ import annotations

__all__ = ["APPROVED_BASENAMES", "APPROVED_SUFFIXES", "EXCLUDED_PATH_PARTS"]

APPROVED_BASENAMES: frozenset[str] = frozenset(
    {
        "topics.py",
        "topics.ts",
        "topics.yaml",
        "topic_constants.py",
        "constants.py",
        "constants_event_types.py",
        "constants_topic_taxonomy.py",
        "platform_topic_suffixes.py",
        "topic_naming_baseline.txt",
        "governance_emitter.py",
        "contract_topic_extractor.py",
        "check_topic_drift.py",
        "validator_topic_suffix.py",
        "topic_allowlist.yaml",
        "topic_registry.yaml",
        "service_topic_registry.py",
        "validation_exemptions.yaml",
    }
)

APPROVED_SUFFIXES: frozenset[str] = frozenset(
    {
        "/contract.yaml",
        "/handler_contract.yaml",
    }
)

# Path parts that are always excluded regardless of contract configuration.
# This provides defense-in-depth for programmatic usage with minimal contracts
# (e.g. tests that construct ModelValidatorSubcontract with exclude_patterns=[]).
EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
    }
)
