# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""In-process runtime, effect wiring, golden report and repository zero target.

A broker overlay pair does not exist yet. These tests exercise the in-memory
inventory overlay and default composition, without inventing broker parity.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.runtime_first_party_ref import (
    create_container,
    run,
)
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
GIT = shutil.which("git") or "git"
FIXTURES = Path(__file__).parents[3] / "fixtures/validation/first_party_ref"
ROOT = Path(__file__).parents[4]
TAG = "dev-20261018024445-b6ee996befa1"


class MemoryInventory:
    def __init__(self):
        self.calls = []

    def handle(self, request):
        self.calls.append(request)
        return ModelFirstPartyTagInventoryResult(repo=request.repo, tags=(TAG,))


def normalized(value):
    if isinstance(value, dict):
        return {
            key: normalized(item)
            for key, item in value.items()
            if key
            not in {
                "run_id",
                "report_id",
                "generated_at",
                "created_at",
                "timestamp",
                "started_at",
                "completed_at",
                "correlation_id",
            }
        }
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def test_runtime_resolves_both_effects_and_matches_golden(tmp_path, monkeypatch):
    fixture = json.loads((FIXTURES / "violation_release_pin.json").read_text())
    for file in fixture["files"]:
        target = tmp_path / file["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file["source"])
    inventory = MemoryInventory()
    container = create_container(inventory)
    report_path = tmp_path / "report.json"
    argv = ["--root", str(tmp_path), "--report-json", str(report_path)]
    resolutions = []
    original = ModelONEXContainer.get_service

    def spy(self, interface, service_name=None):
        resolutions.append(interface.__name__)
        return original(self, interface, service_name)

    with patch.object(ModelONEXContainer, "get_service", spy):
        assert run(argv, container=container) == 1
    assert {
        "NodeFirstPartyTagInventoryEffect",
        "NodeValidationReportWriteEffect",
    } <= set(resolutions)
    assert [call.repo for call in inventory.calls] == ["omnibase_core"]
    assert normalized(json.loads(report_path.read_text())) == json.loads(
        (FIXTURES / "golden_run_event.json").read_text()
    )
    assert report_path.with_name("report.json.events.jsonl").exists()


def test_hook_ids_still_name_new_module():
    hooks = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())
    for hook_id in ("check-action-pins", "check-internal-sibling-pins"):
        hook = next(hook for hook in hooks if hook["id"] == hook_id)
        assert (
            hook["entry"]
            == "python -m omnibase_core.nodes.node_first_party_tag_inventory_effect.runtime_first_party_ref"
        )
        assert hook["pass_filenames"] is False
        assert "--no-staleness" not in hook.get("args", [])


def test_repository_tracked_files_have_zero_issues():
    files = subprocess.check_output(
        [GIT, "ls-files", "-z"],
        cwd=ROOT,
        text=True,
        env={"PATH": str(Path(GIT).parent)},
    ).split("\0")
    # Removed legacy code may still be in the index until the lane stages it.
    paths = [ROOT / name for name in files if name and (ROOT / name).is_file()]
    sources = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["uv"][
        "sources"
    ]
    pins = tuple(
        source["tag"] for source in sources.values() if isinstance(source, dict)
    )

    class PinnedInventory:
        def handle(self, request):
            return ModelFirstPartyTagInventoryResult(repo=request.repo, tags=pins)

    result = ValidatorFirstPartyRef(
        root=ROOT, inventory=PinnedInventory().handle
    ).validate(paths)
    assert result.metadata.files_processed > 50
    assert result.issues == [], [
        (issue.code, str(issue.file_path), issue.message) for issue in result.issues
    ]


@pytest.mark.parametrize("source", ["[project\n", "[tool.uv.sources]\ncore = {git =\n"])
def test_runtime_parse_errors_are_blocking(tmp_path, monkeypatch, source):
    (tmp_path / "pyproject.toml").write_text(source)
    assert (
        run(["--root", str(tmp_path)], container=create_container(MemoryInventory()))
        == 1
    )


def test_empty_tree_and_missing_target_are_blocking(tmp_path):
    container = create_container(MemoryInventory())
    assert run(["--root", str(tmp_path)], container=container) == 1
    assert run(["--root", str(tmp_path), "missing.yml"], container=container) == 1


def test_stale_pin_without_an_inventory_is_blocking(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["omnibase-core>=1"]\n'
    )
    with pytest.raises(ModelOnexError, match="tag inventory"):
        ValidatorFirstPartyRef(root=tmp_path).validate(tmp_path)
