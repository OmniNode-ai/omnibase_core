# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Node-home admission of declared validator nodes, and its contract parameters (OMN-21515).

A new node directory is refused unless its ``contract.yaml`` lists a validator
category under the contract field the ``node-home:node-outside-market`` row names.
Every name, pattern, category and text of the node-home rule group is a
``parameters`` entry of the validator contract; the table below mutates each
key and asserts the verdict of the scenario that key controls.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from omnibase_core.models.validation import ModelNodeHomeRatchetRequest
from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)
from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute import (
    runtime_canonical_file_shape_check as runtime,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    NodeHomeRule,
)
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    NODE_HOME_BASELINE,
    RULES,
    git,
    write,
)

pytestmark = pytest.mark.unit

CONTRACT = ValidatorCanonicalFileShape().contract
ORDINARY = "src/pkg/nodes/node_ordinary"
DECLARED = "src/pkg/nodes/node_declared"


def _request(repo: Path) -> ModelNodeHomeRatchetRequest:
    return runtime.gather_node_home_request(
        runtime.GitRepo(
            repo,
            env=scrub_git_location_env(),
            cat_file_timeout_s=RULES.parameters.cat_file_timeout_s,
        ),
        runtime.INDEX,
        "HEAD",
        RULES.parameters,
    )


def _codes(repo: Path) -> list[tuple[str, str]]:
    git(repo, "add", "-A")
    result = NodeHomeRule(RULES).check(_request(repo))
    return [(finding.code, finding.path) for finding in result.findings]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "dev")
    write(tmp_path, "pyproject.toml", '[project]\nname = "other_repo"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def _plant(repo: Path, directory: str, contract: str) -> None:
    write(repo, f"{directory}/contract.yaml", contract)
    write(repo, f"{directory}/handlers/__init__.py", "")


def test_an_ordinary_new_node_is_refused_and_a_declared_validator_node_admitted(
    repo: Path,
) -> None:
    _plant(repo, ORDINARY, "name: ordinary\n")
    _plant(repo, DECLARED, "name: declared\ntags: [validator_node]\n")
    assert _codes(repo) == [("node-outside-market", ORDINARY)]


def test_a_validator_support_node_is_admitted(repo: Path) -> None:
    _plant(repo, DECLARED, "name: declared\ntags: [other, validator_support_node]\n")
    assert _codes(repo) == []


@pytest.mark.parametrize(
    "contract",
    [
        "name: n\ntags: validator_node\n",
        "name: n\ntags: [compute]\n",
        "name: n\nmetadata:\n  tags: [validator_node]\n",
        "name: n\ntags: [unclosed\n",
        "- a\n- b\n",
    ],
)
def test_a_contract_that_does_not_list_a_category_does_not_admit_its_node(
    repo: Path, contract: str
) -> None:
    _plant(repo, ORDINARY, contract)
    assert _codes(repo) == [("node-outside-market", ORDINARY)]


def test_an_admitted_node_does_not_admit_a_sibling_without_a_declaration(
    repo: Path,
) -> None:
    _plant(repo, DECLARED, "name: declared\ntags: [validator_node]\n")
    _plant(repo, ORDINARY, "name: ordinary\ntags: []\n")
    assert _codes(repo) == [("node-outside-market", ORDINARY)]


def test_admission_does_not_loosen_the_baseline_or_the_registration_rules(
    repo: Path,
) -> None:
    _plant(repo, DECLARED, "name: declared\ntags: [validator_node]\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "admitted node")
    write(repo, NODE_HOME_BASELINE, f"{DECLARED}\nsrc/pkg/nodes/node_gone\n")
    write(
        repo,
        "pyproject.toml",
        '[project]\nname = "other_repo"\n[project.entry-points."onex.nodes"]\nx = "pkg:x"\n',
    )
    assert sorted({code for code, _ in _codes(repo)}) == [
        "baseline-growth",
        "baseline-stale",
        "entry-point-outside-market",
    ]


def test_disabling_the_outside_market_row_admits_the_ordinary_node() -> None:
    rules = RULES.model_copy(
        update={"enabled": RULES.enabled - {"node-home:node-outside-market"}}
    )
    request = _scenario_request(tracked=[f"{ORDINARY}/contract.yaml"], handlers=True)
    assert NodeHomeRule(RULES).check(request).findings
    assert NodeHomeRule(rules).check(request).findings == ()


def test_this_repository_validator_node_declares_its_category() -> None:
    contract = (
        Path(__file__).resolve().parents[4]
        / "src/omnibase_core/nodes/node_canonical_file_shape_check_compute/contract.yaml"
    )
    assert "validator_node" in contract.read_text(encoding="utf-8")


# --- planted violation / clean pair of every node-home row -------------------

NODE_HOME_FIXTURES = (
    Path(__file__).resolve().parents[4]
    / "tests/fixtures/validation/canonical_file_shape/node_home"
)
NODE_HOME_ROWS = sorted(
    rule.rule_id.removeprefix("node-home:")
    for rule in CONTRACT.rules
    if rule.rule_id.startswith("node-home:")
)


def _fixture(name: str) -> ModelNodeHomeRatchetRequest:
    return ModelNodeHomeRatchetRequest.model_validate_json(
        (NODE_HOME_FIXTURES / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("row", NODE_HOME_ROWS)
def test_node_home_violation_fixture_yields_exactly_one_finding_with_its_rule_id(
    row: str,
) -> None:
    findings = NodeHomeRule(RULES).check(_fixture(f"violation_{row}.json")).findings
    assert [finding.code for finding in findings] == [row]


@pytest.mark.parametrize("row", NODE_HOME_ROWS)
def test_node_home_clean_fixture_yields_no_finding(row: str) -> None:
    assert NodeHomeRule(RULES).check(_fixture(f"clean_{row}.json")).findings == ()


@pytest.mark.parametrize("row", NODE_HOME_ROWS)
def test_disabling_a_node_home_row_clears_its_violation_fixture(row: str) -> None:
    rules = RULES.model_copy(update={"enabled": RULES.enabled - {f"node-home:{row}"}})
    assert NodeHomeRule(rules).check(_fixture(f"violation_{row}.json")).findings == ()


# --- every node-home parameter key is mutated by a table row -----------------


def _scenario_request(
    *,
    tracked: list[str],
    handlers: bool = False,
    node_classes: list[str] | None = None,
    contracts: dict[str, str] | None = None,
    head_baseline: str | None = None,
    base_baseline: str | None = None,
    head_entry_points: frozenset[str] = frozenset(),
) -> ModelNodeHomeRatchetRequest:
    paths = list(tracked)
    if handlers:
        paths.extend(f"{path.rsplit('/', 1)[0]}/handlers/h.py" for path in tracked)
    return ModelNodeHomeRatchetRequest(
        tracked_paths=frozenset(paths),
        node_class_paths=frozenset(node_classes or []),
        node_contract_texts=tuple(
            ModelCanonicalFileShapeText(path=path, text=text)
            for path, text in (contracts or {}).items()
        ),
        head_baseline_text=head_baseline,
        base_baseline_text=base_baseline,
        base_node_directories=frozenset(),
        head_entry_points=head_entry_points,
        base_entry_points=frozenset(),
    )


SCENARIOS: dict[str, Callable[[], ModelNodeHomeRatchetRequest]] = {
    "under_tests": lambda: _scenario_request(
        tracked=["tests/pkg/nodes/node_a/contract.yaml"], handlers=True
    ),
    "under_hidden": lambda: _scenario_request(
        tracked=["src/.hid/nodes/node_a/contract.yaml"], handlers=True
    ),
    "class_node": lambda: _scenario_request(
        tracked=["src/pkg/node_a/impl.py"], node_classes=["src/pkg/node_a/impl.py"]
    ),
    "direct_handler": lambda: _scenario_request(
        tracked=["src/pkg/svc/contract.yaml", "src/pkg/svc/handler_a.py"]
    ),
    "node_file": lambda: _scenario_request(
        tracked=["src/pkg/svc/contract.yaml", "src/pkg/svc/node.py"]
    ),
    "handlers_dir": lambda: _scenario_request(
        tracked=["src/pkg/svc/contract.yaml", "src/pkg/svc/handlers/h.py"]
    ),
    "nodes_dir": lambda: _scenario_request(tracked=["src/pkg/nodes/a/contract.yaml"]),
    "declared": lambda: _scenario_request(
        tracked=["src/pkg/nodes/a/contract.yaml"],
        contracts={
            "src/pkg/nodes/a/contract.yaml": "name: a\ntags: [validator_node]\n"
        },
    ),
    "ordinary": lambda: _scenario_request(tracked=["src/pkg/nodes/a/contract.yaml"]),
    "stale": lambda: _scenario_request(
        tracked=[],
        head_baseline="src/pkg/nodes/gone\n",
        base_baseline="src/pkg/nodes/gone\n",
    ),
    "growth": lambda: _scenario_request(
        tracked=["src/pkg/nodes/a/contract.yaml", "src/pkg/nodes/a/handlers/h.py"],
        head_baseline="src/pkg/nodes/a\n",
        base_baseline="",
    ),
    "removed": lambda: _scenario_request(
        tracked=[], head_baseline=None, base_baseline="\n"
    ),
    "entry_point": lambda: _scenario_request(
        tracked=[], head_entry_points=frozenset({"x"})
    ),
}


def _verdict(
    scenario: str, parameters: ModelCanonicalFileShapeRules
) -> list[tuple[str, str, str]]:
    rules = RULES.model_copy(update={"parameters": parameters})
    result = NodeHomeRule(rules).check(SCENARIOS[scenario]())
    return [(f.code, f.path, f.message) for f in result.findings]


INERT = "zz-mutated"
MUTATIONS: dict[str, tuple[str, object]] = {
    "node_home_ignored_components": ("under_tests", ()),
    "node_home_hidden_prefix": ("under_hidden", INERT),
    "node_home_source_suffix": ("class_node", INERT),
    "node_home_handler_prefix": ("direct_handler", INERT),
    "node_home_node_file": ("node_file", INERT),
    "node_home_handlers_dir": ("handlers_dir", INERT),
    "node_home_nodes_dir": ("nodes_dir", INERT),
    "node_home_node_dir_prefix": ("class_node", INERT),
    "node_home_admitted_field": ("declared", INERT),
    "node_home_admitted_categories": ("declared", ()),
    "node_home_entry_point_path": ("entry_point", ("project", "zz")),
    "node_home_outside_market_text": ("ordinary", INERT),
    "node_home_baseline_stale_text": ("stale", INERT),
    "node_home_baseline_growth_text": ("growth", INERT),
    "node_home_baseline_removed_text": ("removed", INERT),
    "node_home_entry_point_text": ("entry_point", INERT),
}
# Read from the repository by the node runtime (git facts), not by the pure rule;
# the tests below mutate them through the runtime.
RUNTIME_KEYS = frozenset({"node_home_node_class_pattern", "cat_file_timeout_s"})


def test_every_node_home_parameter_key_is_mutated_by_a_table_row() -> None:
    declared = {
        key
        for key in ModelCanonicalFileShapeRules.model_fields
        if key.startswith("node_home_") or key == "cat_file_timeout_s"
    }
    # node_home_baseline_path is mutated in the checker table of the file rules.
    assert declared - {"node_home_baseline_path"} == set(MUTATIONS) | RUNTIME_KEYS


@pytest.mark.parametrize("key", sorted(MUTATIONS))
def test_mutating_a_parameter_changes_the_verdict_of_its_scenario(key: str) -> None:
    scenario, inert = MUTATIONS[key]
    before = _verdict(scenario, RULES.parameters)
    after = _verdict(scenario, RULES.parameters.model_copy(update={key: inert}))
    assert before != after, f"{key} does not control the {scenario} scenario"


def test_the_node_class_pattern_controls_class_node_detection(repo: Path) -> None:
    write(repo, "src/pkg/node_cls/impl.py", "class NodeCls:\n    pass\n")
    git(repo, "add", "-A")
    git_repo = runtime.GitRepo(
        repo,
        env=scrub_git_location_env(),
        cat_file_timeout_s=RULES.parameters.cat_file_timeout_s,
    )
    found = runtime.gather_node_home_request(
        git_repo, runtime.INDEX, "HEAD", RULES.parameters
    )
    assert found.node_class_paths == {"src/pkg/node_cls/impl.py"}
    mutated = RULES.parameters.model_copy(
        update={"node_home_node_class_pattern": INERT}
    )
    assert (
        runtime.gather_node_home_request(
            git_repo, runtime.INDEX, "HEAD", mutated
        ).node_class_paths
        == frozenset()
    )


def test_the_git_reader_ceiling_comes_from_the_contract(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[float] = []

    class Spy(runtime.GitRepo):
        def __init__(
            self,
            root: Path,
            env: Mapping[str, str] | None = None,
            *,
            cat_file_timeout_s: float,
        ) -> None:
            seen.append(cat_file_timeout_s)
            super().__init__(root, env, cat_file_timeout_s=cat_file_timeout_s)

    monkeypatch.setattr(runtime, "GitRepo", Spy)
    assert runtime.main(["--repo-root", str(repo), "--rules", "node-home"]) == 0
    assert seen == [RULES.parameters.cat_file_timeout_s]
