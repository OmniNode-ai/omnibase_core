# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Core ships no model ids or inference endpoints of its own (OMN-19391).

Plan task B1 of knowledge-base-internal
``beta/plans/2026-09-23-remove-hardcoded-model-config.md``. The A1 scanner
(OMN-19252) runs over ``src/omnibase_core`` and every model-id (M) or endpoint
(E) finding must sit in a file named in ``_RESIDUAL_FILES`` below. That set is
the whole tolerance, and it only shrinks.

Before B1 this test failed on two files: the generated
``constants/constants_llm_refs.py`` (model keys generated from data owned by
two higher layers) and ``models/configuration/model_tier_config.py`` (tier
defaults naming concrete models). Both were deleted with no shim or alias.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.hardcoded_model_config.handler import scan
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    load_policy,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "omnibase_core"
_SCANNED_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json"})

# Files still carrying an M or E finding, each also in the committed guard
# baseline. Entries only leave this set.
_RESIDUAL_FILES: frozenset[str] = frozenset(
    {
        # Public vendor API URLs in the integrations catalog.
        "src/omnibase_core/contracts/integrations/catalog.yaml",
        # A field default naming a vendor model.
        "src/omnibase_core/models/configuration/model_agent_config.py",
        # Field descriptions quoting an example model id.
        "src/omnibase_core/models/delegation/wire/model_premium_counterfactual.py",
        "src/omnibase_core/models/delegation/wire/model_task_delegated_event.py",
        "src/omnibase_core/models/routing/model_routing_decision.py",
    }
)

# Paths that must never carry a finding again.
_DELETED_B1_FILES: tuple[str, ...] = (
    "src/omnibase_core/constants/constants_llm_refs.py",
    "src/omnibase_core/models/configuration/model_tier_config.py",
)


def _model_and_endpoint_findings() -> dict[str, list[str]]:
    policy = load_policy()
    by_file: dict[str, list[str]] = {}
    for path in sorted(_SRC.rglob("*")):
        if not path.is_file() or path.suffix not in _SCANNED_SUFFIXES:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for finding in scan(rel, text, policy):
            if finding.family in ("M", "E"):
                by_file.setdefault(rel, []).append(
                    f"{finding.line}:{finding.family}:{finding.matched_text}"
                )
    return by_file


def test_no_model_or_endpoint_literal_outside_the_residual_set() -> None:
    findings = _model_and_endpoint_findings()
    unexpected = {
        path: hits for path, hits in findings.items() if path not in _RESIDUAL_FILES
    }
    assert unexpected == {}, (
        "model ids and inference endpoints belong in a config-store overlay "
        f"(llm.catalog, llm.pricing, embedding.endpoint), not in core: {unexpected}"
    )


def test_the_b1_modules_are_gone() -> None:
    present = [p for p in _DELETED_B1_FILES if (_REPO_ROOT / p).exists()]
    assert present == []


def test_the_scan_sees_model_ids_positive_control() -> None:
    # A zero is only evidence when the same scan can return a row (rule 16).
    policy = load_policy()
    planted = 'DEFAULT_MODEL = "claude-opus-4-6"\n'
    hits = scan("src/omnibase_core/planted_probe.py", planted, policy)
    assert [h.family for h in hits] == ["M"]
