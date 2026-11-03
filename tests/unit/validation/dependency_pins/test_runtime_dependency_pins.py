# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Dependency-pin runtime and git effect (OMN-22360).

The runtime runs with file overlays and an in-memory facts effect, and the git
effect runs against local repositories built in the test, so no network is used.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.dependency_direction.model_repo_layer import ModelRepoLayer
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_request import (
    ModelDependencyPinFactsRequest,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_hook_repo import (
    ModelDependencyPinHookRepo,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.nodes.node_dependency_pins_check_effect.handler import (
    NodeDependencyPinsCheckEffect,
)
from omnibase_core.nodes.node_dependency_pins_check_effect.runtime_dependency_pins_check import (
    build_container,
    run,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit


class _FixedFacts(NodeDependencyPinsCheckEffect):
    """An in-memory facts effect: every requested repository has releases 1.0.0 and 1.1.0."""

    def handle(
        self, request: ModelDependencyPinFactsRequest
    ) -> ModelDependencyPinFactsResult:
        return ModelDependencyPinFactsResult(
            inventories=tuple(
                ModelDependencyReleaseInventory(repo=r, versions=("1.0.0", "1.1.0"))
                for r in request.repos
            )
        )


def _overlays(tmp_path: Path, order: dict[str, int]) -> tuple[Path, Path]:
    layers = ModelRepoLayerMap(
        github_org="acme",
        repos=tuple(
            ModelRepoLayer(repo=r, layer=n, distributions=(f"{r}-pkg",))
            for r, n in order.items()
        ),
    )
    policy = ModelDependencyPinPolicy(
        edge_tables=("project",),
        pin_style="range",
        release_tag_pattern=r"^v(?P<version>[0-9]+(?:\.[0-9]+)*)$",
        tag_inventory_url="https://example.invalid/{org}/{repo}.git",
        max_releases_behind=0,
        specifier_must_admit_newest_release=True,
        hook_rev_max_releases_behind=0,
    )
    layer_file = tmp_path / f"layers-{'-'.join(order)}.yaml"
    policy_file = tmp_path / "policy.yaml"
    layer_file.write_text(yaml.safe_dump(layers.model_dump(mode="json")), "utf-8")
    policy_file.write_text(yaml.safe_dump(policy.model_dump(mode="json")), "utf-8")
    return layer_file, policy_file


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "upper-pkg"\ndependencies = ["lower-pkg>=1.1,<2"]\n',
        "utf-8",
    )
    return root


def test_runtime_passes_and_fails_with_file_overlays(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    report = tmp_path / "report.json"
    good_layers, policy = _overlays(tmp_path, {"lower": 0, "upper": 1})
    bad_layers, _ = _overlays(tmp_path, {"upper": 0, "lower": 1})
    argv = [str(root), "--policy", str(policy), "--report-json", str(report)]
    good = run(
        [*argv, "--layer-order", str(good_layers)],
        container=build_container(facts_source=_FixedFacts()),
    )
    assert good == 0
    assert json.loads(report.read_text("utf-8"))["overall_status"] == "PASS"
    bad = run(
        [*argv, "--layer-order", str(bad_layers)],
        container=build_container(facts_source=_FixedFacts()),
    )
    assert bad == 1
    findings = json.loads(report.read_text("utf-8"))["findings"]
    assert [f["rule_id"] for f in findings] == ["layer_order"]


def test_runtime_refuses_a_tree_with_no_manifest(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    code = run([str(empty)], container=build_container(facts_source=_FixedFacts()))
    assert code == 1


def _git(*args: str, cwd: Path, when: int | None = None) -> str:
    identity = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    if when is not None:
        identity["GIT_COMMITTER_DATE"] = f"{when} +0000"
        identity["GIT_AUTHOR_DATE"] = f"{when} +0000"
    git = shutil.which("git")
    assert git is not None
    return subprocess.run(
        [git, *args],
        cwd=cwd,
        env=scrub_git_location_env({"HOME": str(cwd), **identity}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _history_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository with an old commit, then two release tags and a dev tag."""
    work = tmp_path / "acme" / "hooks"
    work.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=work)
    _git("commit", "-q", "--allow-empty", "-m", "old", cwd=work, when=1000)
    old = _git("rev-parse", "HEAD", cwd=work)
    for stamp, tag in ((2000, "v1.0.0"), (3000, "v1.1.0"), (4000, "dev-x")):
        _git("commit", "-q", "--allow-empty", "-m", tag, cwd=work, when=stamp)
        _git("tag", "-a", "-m", tag, tag, cwd=work, when=stamp)
    return work, old


def _effect_request(
    tmp_path: Path, hook_url: str, history: str | None, *pins: str
) -> ModelDependencyPinFactsRequest:
    return ModelDependencyPinFactsRequest(
        github_org="acme",
        repos=("hooks", "missing"),
        hook_pins=tuple(
            ModelPrecommitPin(repo=hook_url, rev=rev, line=1, hook_ids=("h",))
            for rev in pins
        ),
        policy=ModelDependencyPinPolicy(
            edge_tables=("project",),
            pin_style="range",
            release_tag_pattern=r"^v(?P<version>[0-9]+(?:\.[0-9]+)*)$",
            tag_inventory_url=f"{tmp_path}{os.sep}{{org}}{os.sep}{{repo}}",
            max_releases_behind=0,
            specifier_must_admit_newest_release=True,
            hook_repos=(ModelDependencyPinHookRepo(url=hook_url, repo="hooks"),),
            hook_rev_max_releases_behind=0,
        ),
        hook_history_dir=history,
        git_timeout_seconds=60,
    )


def test_effect_reads_release_tags_and_hook_history(tmp_path: Path) -> None:
    work, old = _history_repo(tmp_path)
    request = _effect_request(tmp_path, str(work), str(work), old, "dev-x", "nope")
    result = NodeDependencyPinsCheckEffect().handle(request)
    inventories = {i.repo: i for i in result.inventories}
    assert sorted(inventories["hooks"].versions) == ["1.0.0", "1.1.0"]
    assert inventories["missing"].error
    (history,) = result.hook_histories
    assert history.error is None
    assert {t.rev: t.committed_at for t in history.rev_times} == {
        old: 1000,
        "dev-x": 4000,
    }
    assert history.release_times == (2000, 3000)


def test_effect_clones_the_hook_history_when_none_is_given(tmp_path: Path) -> None:
    work, old = _history_repo(tmp_path)
    request = _effect_request(tmp_path, str(work), None, old)
    (history,) = NodeDependencyPinsCheckEffect().handle(request).hook_histories
    assert history.error is None
    assert [t.rev for t in history.rev_times] == [old]
    assert history.release_times == (2000, 3000)


def test_effect_reports_a_failed_clone_as_an_error(tmp_path: Path) -> None:
    missing = str(tmp_path / "acme" / "absent")
    request = _effect_request(tmp_path, missing, None, "abc")
    (history,) = NodeDependencyPinsCheckEffect().handle(request).hook_histories
    assert history.error
