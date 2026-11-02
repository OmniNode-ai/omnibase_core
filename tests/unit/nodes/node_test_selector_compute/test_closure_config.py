# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-14206: a repository sets its closure candidate roots in its selector
policy YAML, not in Python.

The packaged ``compute_closure_selection`` takes ``candidate_roots``,
``test_file_patterns`` and ``ignored_prefixes``, but the policy model every
repository loads (``ModelAdjacencyMap``) had no field for them, so a
repository whose tests live outside ``tests/unit/`` could only change them by
editing code. These tests pin the ``closure:`` block of the policy model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyMap,
)
from omnibase_core.models.nodes.test_selector.model_closure_config import (
    ModelClosureConfig,
)
from omnibase_core.nodes.node_test_selector_compute.closure_selector import (
    DEFAULT_CANDIDATE_ROOTS,
    DEFAULT_IGNORED_PREFIXES,
    DEFAULT_TEST_FILE_PATTERNS,
    compute_policy_closure,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_POLICY = REPO_ROOT / "scripts" / "ci" / "test_selection_adjacency.yaml"

_BASE_YAML = """\
schema_version: 1
shared_modules: [models]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: [tests/conftest.py]
"""


def test_config_defaults_match_the_packaged_selector_defaults() -> None:
    """The model's defaults and the selector's defaults are one answer."""
    config = ModelClosureConfig()
    assert config.candidate_roots == DEFAULT_CANDIDATE_ROOTS
    assert config.test_file_patterns == DEFAULT_TEST_FILE_PATTERNS
    assert config.ignored_prefixes == DEFAULT_IGNORED_PREFIXES


def test_policy_without_closure_block_gets_the_defaults() -> None:
    policy = ModelAdjacencyMap.from_yaml_text(_BASE_YAML)
    assert policy.closure == ModelClosureConfig()


def test_policy_closure_block_sets_roots_patterns_and_prefixes() -> None:
    policy = ModelAdjacencyMap.from_yaml_text(
        _BASE_YAML
        + """\
closure:
  candidate_roots: [tests/unit, tests/nodes/]
  test_file_patterns: ["test_*.py", "*_test.py"]
  ignored_prefixes: [tests/integration/, tests/e2e]
"""
    )
    assert policy.closure.candidate_roots == ("tests/unit/", "tests/nodes/")
    assert policy.closure.test_file_patterns == ("test_*.py", "*_test.py")
    assert policy.closure.ignored_prefixes == ("tests/integration/", "tests/e2e/")


def test_core_policy_file_keeps_the_historical_unit_only_closure() -> None:
    """omnibase_core's own selection is unchanged by this field."""
    policy = ModelAdjacencyMap.from_yaml_text(CORE_POLICY.read_text("utf-8"))
    assert policy.closure.candidate_roots == ("tests/unit/",)
    assert policy.closure == ModelClosureConfig()


@pytest.mark.parametrize(
    "roots",
    [
        [],
        [""],
        ["/"],
        ["/abs/tests/"],
        ["tests/../src/"],
        ["tests/", "tests/unit/"],
    ],
    ids=["empty", "blank", "slash", "absolute", "dotdot", "nested"],
)
def test_malformed_candidate_roots_are_refused_at_load(roots: list[str]) -> None:
    """A bad root is a load error, never an empty candidate universe."""
    with pytest.raises(ValidationError):
        ModelClosureConfig(candidate_roots=tuple(roots))


def test_empty_test_file_patterns_are_refused() -> None:
    with pytest.raises(ValidationError):
        ModelClosureConfig(test_file_patterns=())
    with pytest.raises(ValidationError):
        ModelClosureConfig(test_file_patterns=("",))


def test_validation_error_preserves_dynamic_path_text() -> None:
    root = "tests/{message}/../unit/"
    with pytest.raises(ValidationError) as exc_info:
        ModelClosureConfig(candidate_roots=(root,))

    error = exc_info.value.errors()[0]
    assert error["type"] == "closure_config"
    assert (
        error["msg"] == f"candidate root must be repo-relative with no '..': {root!r}"
    )


def test_ignored_prefix_inside_a_candidate_root_is_refused() -> None:
    """A candidate root wins over an ignored prefix, so an overlap would
    silently do nothing; refuse it instead."""
    with pytest.raises(ValidationError):
        ModelClosureConfig(
            candidate_roots=("tests/",), ignored_prefixes=("tests/integration/",)
        )


def test_unknown_closure_key_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelAdjacencyMap.from_yaml_text(
            _BASE_YAML + "closure:\n  candidate_root: [tests/nodes/]\n"
        )


def test_policy_closure_roots_select_a_dependent_outside_tests_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end over a real import graph: a policy-declared tests/nodes/ root
    makes the closure select a dependent test there; the default policy cannot."""
    pkg = "omn14206_policy_pkg"
    repo = tmp_path / "repo"
    files = {
        f"src/{pkg}/__init__.py": "",
        f"src/{pkg}/leaf.py": "X = 1\n",
        "tests/unit/m/test_unrelated.py": "import os\n",
        "tests/nodes/n/test_node_leaf.py": f"from {pkg}.leaf import X\n",
    }
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    monkeypatch.syspath_prepend(str(repo / "src"))
    changed = [f"src/{pkg}/leaf.py"]

    default = compute_policy_closure(changed, repo, ModelClosureConfig(), pkg)
    configured = compute_policy_closure(
        changed,
        repo,
        ModelClosureConfig(candidate_roots=("tests/unit/", "tests/nodes/")),
        pkg,
    )

    assert "tests/nodes/n/test_node_leaf.py" not in default.selected_files
    assert configured.fail_closed is False
    assert "tests/nodes/n/test_node_leaf.py" in configured.selected_files
