# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Keep repository-owned hooks local after OCC retirement S8 (OMN-20068)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
SKIP_FILE = REPO_ROOT / ".github" / "precommit-suite-skip.yaml"
EXPORTED_HOOKS = REPO_ROOT / ".pre-commit-hooks.yaml"


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict), "expected a YAML mapping"
    result: dict[str, object] = {}
    for key, item in value.items():
        assert isinstance(key, str), "expected string mapping keys"
        result[key] = item
    return result


def _mappings(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list), "expected a YAML list of mappings"
    return [_mapping(item) for item in value]


def _repos() -> list[dict[str, object]]:
    config = _mapping(yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8")))
    return _mappings(config["repos"])


def _matching_hooks(hook_id: str) -> list[tuple[str, dict[str, object]]]:
    matches: list[tuple[str, dict[str, object]]] = []
    for repo in _repos():
        repo_name = repo["repo"]
        assert isinstance(repo_name, str), "expected a string repository name"
        for hook in _mappings(repo.get("hooks", [])):
            if hook.get("id") == hook_id:
                matches.append((repo_name, hook))
    return matches


def test_no_untracked_todos_is_a_local_hook_running_the_in_repo_handler() -> None:
    """Catch duplicate TODO hooks or a return to the external implementation."""
    matches = _matching_hooks("no-untracked-todos")
    assert len(matches) == 1
    repo, hook = matches[0]
    assert repo == "local"
    entry = hook["entry"]
    assert isinstance(entry, str)
    assert "omnibase_core.handlers.handler_todo_format" in entry


def test_no_untyped_metadata_runs_the_in_repo_script() -> None:
    """Catch duplicate metadata hooks or reuse of the retired console script."""
    matches = _matching_hooks("no-untyped-metadata")
    assert len(matches) == 1
    repo, hook = matches[0]
    assert repo == "local"
    entry = hook["entry"]
    assert isinstance(entry, str)
    assert "scripts/check_no_untyped_metadata.py" in entry
    assert "check-no-untyped-metadata" not in entry


def test_no_hook_in_the_onex_change_control_block_is_one_this_repo_owns() -> None:
    """Catch repository-owned hooks returning to the OCC repository block."""
    owned_ids = {"no-untracked-todos", "no-untyped-metadata"}
    for repo in _repos():
        repo_name = repo["repo"]
        assert isinstance(repo_name, str)
        if repo_name.endswith("onex_change_control"):
            for hook in _mappings(repo.get("hooks", [])):
                hook_id = hook["id"]
                assert isinstance(hook_id, str)
                assert hook_id not in owned_ids


def test_the_in_repo_todo_hook_is_not_excused_from_the_remote_suite() -> None:
    """Catch the local TODO hook being skipped by the remote pre-commit suite."""
    skipped: object = yaml.safe_load(SKIP_FILE.read_text(encoding="utf-8"))
    assert isinstance(skipped, list), "expected a YAML list of hook ids"
    for hook_id in skipped:
        assert isinstance(hook_id, str)
    assert "no-untracked-todos" not in skipped


def test_the_in_repo_todo_hook_is_exported_under_the_same_id() -> None:
    """Catch removal or entry drift of the TODO hook exported to consumers."""
    hooks = _mappings(yaml.safe_load(EXPORTED_HOOKS.read_text(encoding="utf-8")))
    assert any(
        hook.get("id") == "no-untracked-todos"
        and hook.get("entry") == "python -m omnibase_core.handlers.handler_todo_format"
        for hook in hooks
    )
