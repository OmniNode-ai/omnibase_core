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


def test_no_untyped_metadata_runs_the_in_repo_node() -> None:
    """Catch duplicate metadata hooks or reuse of the retired console script."""
    matches = _matching_hooks("no-untyped-metadata")
    assert len(matches) == 1
    repo, hook = matches[0]
    assert repo == "local"
    entry = hook["entry"]
    assert isinstance(entry, str)
    assert "omnibase_core.nodes.node_no_untyped_metadata_check_compute" in entry
    assert "check-no-untyped-metadata" not in entry


def test_no_hardcoded_topics_runs_the_in_repo_handler_with_the_unchanged_exclude() -> (
    None
):
    """Catch a duplicate topic hook, a return to the OCC block or a moved exclude."""
    matches = _matching_hooks("no-hardcoded-topics")
    assert len(matches) == 1
    repo, hook = matches[0]
    assert repo == "local"
    entry = hook["entry"]
    assert isinstance(entry, str)
    assert "omnibase_core.handlers.handler_no_hardcoded_topics" in entry
    assert hook["types_or"] == ["python", "yaml", "ts", "javascript"]
    exclude = hook["exclude"]
    assert isinstance(exclude, str)
    # The 13 pre-existing violations the OCC block excluded, byte for byte.
    assert exclude == (
        r"^(src/omnibase_core/constants/constants_event_types\.py"
        r"|src/omnibase_core/models/events/contract_registration/model_contract_deregistered_event\.py"
        r"|src/omnibase_core/models/events/contract_registration/model_contract_registered_event\.py"
        r"|src/omnibase_core/models/events/contract_registration/model_node_heartbeat_event\.py"
        r"|src/omnibase_core/models/events/model_episode_event\.py"
        r"|src/omnibase_core/models/events/model_git_hook_event\.py"
        r"|src/omnibase_core/models/events/model_github_pr_status_event\.py"
        r"|src/omnibase_core/models/events/model_linear_snapshot_event\.py"
        r"|src/omnibase_core/models/events/validation/model_validation_run_completed_event\.py"
        r"|src/omnibase_core/models/events/validation/model_validation_run_started_event\.py"
        r"|src/omnibase_core/models/events/validation/model_validation_violations_batch_event\.py"
        r"|src/omnibase_core/schemas/cli_contribution\.v1\.example\.yaml"
        r"|src/omnibase_core/validation/validator_topic_suffix\.py)$"
    )


def test_no_hook_in_the_onex_change_control_block_is_one_this_repo_owns() -> None:
    """Catch repository-owned hooks returning to the OCC repository block."""
    owned_ids = {"no-untracked-todos", "no-untyped-metadata", "no-hardcoded-topics"}
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


def test_the_in_repo_topic_hook_is_exported_under_the_same_id() -> None:
    """Catch removal or drift of the hook consumers switch to by repo: and rev: only."""
    hooks = _mappings(yaml.safe_load(EXPORTED_HOOKS.read_text(encoding="utf-8")))
    exported = [hook for hook in hooks if hook.get("id") == "no-hardcoded-topics"]
    assert len(exported) == 1
    hook = exported[0]
    assert (
        hook.get("entry")
        == "python -m omnibase_core.handlers.handler_no_hardcoded_topics"
    )
    assert hook.get("language") == "python"
    assert hook.get("types_or") == ["python", "yaml", "ts", "javascript"]
