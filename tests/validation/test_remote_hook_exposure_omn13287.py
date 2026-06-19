#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Assert W10B (OMN-13287) remote pre-commit hook exposure for the consolidated
fail-closed validators: enum-governance and no-backward-compat.

These hooks are consumed by downstream repos (omnimemory, omniclaude) in place of
their deleted local copies. The contract under test is purely structural: the hook
IDs exist in ``.pre-commit-hooks.yaml`` with the canonical core entrypoints, so a
single implementation backs every consumer.

pydantic-conventions is intentionally NOT exposed here: its core default contract
ships ``fail_on_error: false`` (577 grandfathered core violations), so the validator
detects but cannot block. Exposing it would ship a warn-only gate, which
``feedback_gates_block_no_bypass`` forbids. Tracked as a follow-up (flip
fail_on_error after the core debt burn-down).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_FILE = REPO_ROOT / ".pre-commit-hooks.yaml"

# hook_id -> substring that MUST appear in the hook's entry (canonical core impl).
EXPECTED_HOOKS: dict[str, str] = {
    "check-enum-governance": "omnibase_core.validation.checker_enum_governance",
    "check-no-backward-compat": (
        "scripts/validation/validate-no-backward-compatibility.py"
    ),
}


@pytest.fixture(scope="module")
def hooks() -> dict[str, dict[str, object]]:
    raw = yaml.safe_load(HOOKS_FILE.read_text(encoding="utf-8"))
    assert isinstance(raw, list), ".pre-commit-hooks.yaml must be a list of hooks"
    by_id: dict[str, dict[str, object]] = {}
    for entry in raw:
        assert isinstance(entry, dict)
        hook_id = entry.get("id")
        assert isinstance(hook_id, str)
        by_id[hook_id] = entry
    return by_id


@pytest.mark.unit
@pytest.mark.parametrize("hook_id", sorted(EXPECTED_HOOKS))
def test_w10b_hook_id_present(
    hooks: dict[str, dict[str, object]], hook_id: str
) -> None:
    assert hook_id in hooks, (
        f"W10B remote hook {hook_id!r} missing from .pre-commit-hooks.yaml; "
        "downstream repos cannot consume the canonical core validator."
    )


@pytest.mark.unit
@pytest.mark.parametrize(("hook_id", "entry_substr"), sorted(EXPECTED_HOOKS.items()))
def test_w10b_hook_entry_points_at_core_impl(
    hooks: dict[str, dict[str, object]], hook_id: str, entry_substr: str
) -> None:
    entry = hooks[hook_id].get("entry")
    assert isinstance(entry, str)
    assert entry_substr in entry, (
        f"Hook {hook_id!r} entry {entry!r} does not invoke the canonical core "
        f"validator ({entry_substr!r})."
    )


@pytest.mark.unit
def test_w10b_no_backward_compat_uses_script_language(
    hooks: dict[str, dict[str, object]],
) -> None:
    """The no-backward-compat validator is a scripts/ file not packaged in the
    wheel, so it must run via language: script (the repo is checked out for
    remote consumers) rather than language: python (isolated wheel install)."""
    assert hooks["check-no-backward-compat"].get("language") == "script"


@pytest.mark.unit
def test_w10b_enum_governance_uses_python_language(
    hooks: dict[str, dict[str, object]],
) -> None:
    """Module-importable validators run via language: python so the core wheel is
    installed into the consumer's isolated hook env."""
    assert hooks["check-enum-governance"].get("language") == "python"
    entry = hooks["check-enum-governance"].get("entry")
    assert isinstance(entry, str)
    assert entry.startswith("python -m ")


@pytest.mark.unit
def test_w10b_pydantic_conventions_not_exposed_as_blocking_gate(
    hooks: dict[str, dict[str, object]],
) -> None:
    """pydantic-conventions must NOT be exposed until its core default contract
    flips fail_on_error to true. Until then it detects but cannot block, and a
    warn-only gate is forbidden by feedback_gates_block_no_bypass."""
    assert "check-pydantic-conventions" not in hooks
