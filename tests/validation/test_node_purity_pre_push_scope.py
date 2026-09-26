"""Guard the local node-purity scope and its full-tree CI backstop."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _local_hook() -> dict[str, object]:
    config = yaml.safe_load(
        (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    for repository in config["repos"]:
        for hook in repository.get("hooks", []):
            if hook.get("id") == "check-node-purity":
                return hook
    raise AssertionError("check-node-purity hook is missing")


def test_local_node_purity_matches_only_existing_discovery_paths() -> None:
    hook = _local_hook()
    entry = hook["entry"]
    files = hook["files"]

    assert entry == "uv run python scripts/check_node_purity.py --file"
    assert hook["pass_filenames"] is True
    assert hook["stages"] == ["pre-push"]
    assert hook.get("always_run", False) is False
    assert isinstance(files, str)
    file_pattern = re.compile(files)
    assert file_pattern.search("src/omnibase_core/nodes/node_example.py")
    assert file_pattern.search("src/omnibase_core/infrastructure/node_example.py")
    assert not file_pattern.search(
        "src/omnibase_core/nodes/node_example/handlers/handler_example.py"
    )


def test_ci_retains_full_node_purity_discovery() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "node-purity-check:" in workflow
    assert "python3 scripts/check_node_purity.py --verbose" in workflow
