# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure checker tests for the canonical-file-shape rules (OMN-21515).

Facts in, issues out: the checker runs below with every ``open`` and ``Path``
read patched to raise. Each rule has a ``violation_`` fixture that yields exactly
one issue with that rule id and a ``clean_`` fixture that yields none. A
table-driven test then mutates every ``parameters`` key of the contract and
asserts the verdict change on the scenario that key controls.
"""

from __future__ import annotations

import builtins
import contextlib
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

import omnibase_core.validation.validator_event_registry_drift as drift_validator
from omnibase_core.enums import EnumSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_canonical_file_shape_check_input import (
    ModelCanonicalFileShapeCheckInput,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.models.validation.model_canonical_file_shape_rule_set import (
    ModelCanonicalFileShapeRuleSet,
)
from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.handler import (
    NodeCanonicalFileShapeCheckCompute,
)
from omnibase_core.validation.checker_canonical_file_shape import (
    check,
    load_rule_set,
)
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests/fixtures/validation/canonical_file_shape"
CONTRACT = ValidatorCanonicalFileShape().contract
RULES = load_rule_set(CONTRACT)
FIXTURE_RULES = sorted(
    path.name.removeprefix("violation_").removesuffix(".json")
    for path in FIXTURES.glob("violation_*.json")
)
NOQA = "# " + "no" + "qa"


def _facts(name: str) -> ModelCanonicalFileShapeFacts:
    return ModelCanonicalFileShapeFacts.model_validate_json(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


@contextlib.contextmanager
def forbid_io() -> Iterator[None]:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the checker performed I/O")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(builtins, "open", refuse)
        for name in ("read_text", "read_bytes", "open"):
            patch.setattr(Path, name, refuse)
        yield


def _run(
    facts: ModelCanonicalFileShapeFacts, rules: ModelCanonicalFileShapeRuleSet
) -> tuple[ModelValidationIssue, ...]:
    with forbid_io():
        return check(facts, rules)


def _codes(
    facts: ModelCanonicalFileShapeFacts, rules: ModelCanonicalFileShapeRuleSet = RULES
) -> list[str]:
    return sorted(issue.code or "" for issue in _run(facts, rules))


def _messages(
    facts: ModelCanonicalFileShapeFacts, rules: ModelCanonicalFileShapeRuleSet = RULES
) -> list[tuple[str, str, str]]:
    return sorted(
        (issue.code or "", str(issue.file_path), issue.message)
        for issue in _run(facts, rules)
    )


def test_every_contract_rule_has_a_planted_fixture_pair() -> None:
    checked = {
        rule.rule_id
        for rule in CONTRACT.rules
        if rule.rule_id in RULES.enabled and rule.rule_id in FIXTURE_RULES
    }
    config_only = {
        "declared-gate-lists",
        "repository-lifecycle",
        "git-reader",
        "burndown-baseline",
    }
    # The node-home rows read a node inventory, not file-shape facts; their planted
    # pairs live in fixtures/.../node_home and run in test_node_home_admission.py.
    node_home = {
        rule.rule_id for rule in CONTRACT.rules if rule.rule_id.startswith("node-home:")
    }
    assert checked | config_only | node_home == {
        rule.rule_id for rule in CONTRACT.rules
    }
    for rule in FIXTURE_RULES:
        assert (FIXTURES / f"clean_{rule}.json").is_file()


@pytest.mark.parametrize("rule", FIXTURE_RULES)
def test_violation_fixture_yields_exactly_one_issue_with_its_rule_id(rule: str) -> None:
    assert _codes(_facts(f"violation_{rule}.json")) == [rule]


@pytest.mark.parametrize("rule", FIXTURE_RULES)
def test_clean_fixture_yields_no_issue(rule: str) -> None:
    assert _codes(_facts(f"clean_{rule}.json")) == []


@pytest.mark.parametrize("rule", FIXTURE_RULES)
def test_disabling_a_rule_row_clears_its_violation_fixture(rule: str) -> None:
    rules = RULES.model_copy(update={"enabled": RULES.enabled - {rule}})
    assert _codes(_facts(f"violation_{rule}.json"), rules) == []


def test_new_scripts_file_in_any_repository_is_refused() -> None:
    """AC2: a new scripts/x.py is refused (omnimarket included)."""
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {"head_tree": {"files": ["scripts/x.py", "src/omnimarket/nodes/n/handler.py"]}}
    )
    assert _codes(facts) == ["noncanonical-file"]
    assert [str(i.file_path) for i in check(facts, RULES)] == ["scripts/x.py"]


def test_drift_source_parser_has_canonical_unbound_location() -> None:
    """The drift validator's pure parser must not occupy an unbound handler path."""
    parser_path = (
        "src/"
        + drift_validator.parse_registration_contract.__module__.replace(".", "/")
        + ".py"
    )
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {"head_tree": {"files": [parser_path]}}
    )
    assert _codes(facts) == []


def test_report_has_one_finding_per_refused_path_with_its_rule_id() -> None:
    """AC1: the node returns one finding per refused path, each with a rule id."""
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {
                "files": [
                    "scripts/a.py",
                    "tools/b.sh",
                    "src/pkg/handlers/handler_y.py",
                    "src/pkg/models/model_ok.py",
                ]
            }
        }
    )
    report = NodeCanonicalFileShapeCheckCompute().handle(
        ModelCanonicalFileShapeCheckInput(facts=facts, contract=CONTRACT)
    )
    found = sorted((f.location or "", f.rule_id or "") for f in report.findings)
    assert found == [
        ("scripts/a.py:1", "noncanonical-file"),
        ("src/pkg/handlers/handler_y.py:1", "handler_outside_node"),
        ("tools/b.sh:1", "noncanonical-file"),
    ]
    assert report.overall_status == "FAIL"


def _lifecycle(
    state: str | None,
    changes: list[dict[str, Any]],
    messages: list[str] | None = None,
    head_state: str | None = None,
) -> ModelCanonicalFileShapeFacts:
    return ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {"files": [c["path"] for c in changes]},
            "has_base": True,
            "base_lifecycle_text": None if state is None else f"state: {state}\n",
            "head_lifecycle_text": None
            if (head_state or state) is None
            else f"state: {head_state or state}\n",
            "changes": changes,
            "commit_messages": messages,
        }
    )


def _change(
    path: str, new: str, old: str | None = None, status: str = "M"
) -> dict[str, Any]:
    return {"status": status, "path": path, "new_text": new, "old_text": old}


def test_no_code_refuses_a_new_source_file_and_admits_a_ledger_append() -> None:
    """AC3: no-code refuses src/.../x.py and admits a Markdown ledger-row append."""
    refused = _lifecycle(
        "no-code", [_change("src/pkg/models/x.py", "x = 1\n", None, "A")]
    )
    admitted = _lifecycle(
        "no-code", [_change("docs/ledger.md", "row 1\nrow 2\n", "row 1\n")]
    )
    assert _codes(refused) == ["lifecycle-no-code"]
    assert _codes(admitted) == []


def test_no_code_refuses_growth_of_an_existing_code_file() -> None:
    grown = _lifecycle(
        "no-code",
        [_change("src/pkg/models/m.py", "a = 1\nb = 2\n", "a = 1\n")],
    )
    shrunk = _lifecycle(
        "no-code",
        [_change("src/pkg/models/m.py", "a = 1\n", "a = 1\nb = 2\n")],
    )
    assert _codes(grown) == ["lifecycle-no-code"]
    assert _codes(shrunk) == []


def test_fix_only_new_file_two_line_fix_and_trailer() -> None:
    """AC4: new file refused; two-line fix refused without the trailer, admitted with it."""
    old, new = "a = 1\nb = 2\n", "a = 1\nb = 2\nc = 3\nd = 4\n"
    new_file = _lifecycle(
        "fix-only", [_change("src/pkg/models/n.py", "x = 1\n", None, "A")], ["fix\n"]
    )
    bare = _lifecycle(
        "fix-only", [_change("src/pkg/models/m.py", new, old)], ["fix a bug\n"]
    )
    stamped = _lifecycle(
        "fix-only",
        [_change("src/pkg/models/m.py", new, old)],
        ["fix a bug\n\nrelease=2026-10-29T01:00:00Z\n"],
    )
    assert _codes(new_file) == ["lifecycle-fix-only-new-file"]
    assert _codes(bare) == ["lifecycle-fix-only-growth"]
    assert _codes(stamped) == []


def test_fix_only_growth_is_deferred_when_no_commit_message_is_known() -> None:
    unknown = _lifecycle(
        "fix-only",
        [_change("src/pkg/models/m.py", "a = 1\nb = 2\n", "a = 1\n")],
        None,
    )
    assert _codes(unknown) == []


def test_fix_only_blank_release_stamp_is_not_a_stamp() -> None:
    blank = _lifecycle(
        "fix-only",
        [_change("src/pkg/models/m.py", "a = 1\nb = 2\n", "a = 1\n")],
        ["fix\n\nrelease=\n"],
    )
    assert _codes(blank) == ["lifecycle-fix-only-growth"]


def test_retired_refuses_everything_except_deletions() -> None:
    edits = _lifecycle(
        "retired",
        [
            _change("docs/a.md", "x\n", "y\n"),
            _change("src/pkg/models/m.py", "x = 1\n", None, "A"),
        ],
    )
    nothing = _lifecycle("retired", [])
    assert _codes(edits) == ["lifecycle-retired", "lifecycle-retired"]
    assert _codes(nothing) == []


def test_flipping_the_lifecycle_down_in_the_same_change_does_not_admit_it() -> None:
    flipped = _lifecycle(
        "no-code",
        [_change("src/pkg/models/x.py", "x = 1\n", None, "A")],
        head_state="active",
    )
    assert _codes(flipped) == ["lifecycle-no-code"]


def test_unknown_lifecycle_state_is_an_issue_on_the_lifecycle_file() -> None:
    facts = _lifecycle("sleeping", [_change("docs/a.md", "x\n", "y\n")])
    assert [(i.code, str(i.file_path)) for i in check(facts, RULES)] == [
        ("repository-lifecycle", RULES.parameters.lifecycle_path)
    ]


def test_active_and_undeclared_lifecycle_admit_everything() -> None:
    change = [_change("src/pkg/models/x.py", "x = 1\n", None, "A")]
    assert _codes(_lifecycle("active", change)) == []
    assert _codes(_lifecycle(None, change)) == []


def test_an_unbound_handler_is_refused_while_a_bound_one_keeps_its_directory() -> None:
    """K2: handlers/ stays canonical for a bound handler."""
    assert _codes(_facts("violation_handler_outside_node.json")) == [
        "handler_outside_node"
    ]
    assert _codes(_facts("clean_handler_outside_node.json")) == []


def test_a_console_script_to_a_non_runtime_module_is_refused() -> None:
    """K2: a [project.scripts] entry whose module is not a node runtime."""
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {
                "files": [
                    "src/pkg/handlers/handler_y.py",
                    "src/pkg/nodes/node_y/contract.yaml",
                ],
                "contract_texts": [
                    {
                        "path": "src/pkg/nodes/node_y/contract.yaml",
                        "text": "handler:\n  module: pkg.handlers.handler_y\n",
                    }
                ],
                "pyproject_text": '[project.scripts]\ny = "pkg.handlers.handler_y:main"\n',
            }
        }
    )
    assert _codes(facts) == ["cli_entry_outside_node"]


def test_a_rule_that_is_not_a_file_rule_never_fires_on_a_tree_alone() -> None:
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {"head_tree": {"files": ["src/pkg/models/model_a.py", "docs/a.md"]}}
    )
    assert _codes(facts) == []


# --- contract load -----------------------------------------------------------


def _contract_with(
    mutate: Callable[[list[ModelValidatorRule]], list[ModelValidatorRule]],
) -> ModelValidatorSubcontract:
    return CONTRACT.model_copy(update={"rules": mutate(list(CONTRACT.rules))})


def test_a_contract_missing_a_parameter_fails_to_load() -> None:
    def drop(rules: list[ModelValidatorRule]) -> list[ModelValidatorRule]:
        row = rules[0]
        assert row.parameters
        key = next(iter(row.parameters))
        trimmed = {k: v for k, v in row.parameters.items() if k != key}
        return [row.model_copy(update={"parameters": trimmed}), *rules[1:]]

    with pytest.raises(ModelOnexError):
        load_rule_set(_contract_with(drop))


def test_a_contract_with_an_unknown_parameter_fails_to_load() -> None:
    def add(rules: list[ModelValidatorRule]) -> list[ModelValidatorRule]:
        row = rules[0]
        extra = {**(row.parameters or {}), "unknown_key": "x"}
        return [row.model_copy(update={"parameters": extra}), *rules[1:]]

    with pytest.raises(ModelOnexError):
        load_rule_set(_contract_with(add))


def test_a_contract_declaring_a_parameter_twice_fails_to_load() -> None:
    def duplicate(rules: list[ModelValidatorRule]) -> list[ModelValidatorRule]:
        first = rules[0]
        assert first.parameters
        key, value = next(iter(first.parameters.items()))
        other = rules[1].model_copy(
            update={"parameters": {**(rules[1].parameters or {}), key: value}}
        )
        return [first, other, *rules[2:]]

    with pytest.raises(ModelOnexError):
        load_rule_set(_contract_with(duplicate))


def test_a_node_given_an_invalid_contract_reports_an_error_not_a_pass() -> None:
    invalid = _contract_with(lambda rules: rules[1:])
    report = NodeCanonicalFileShapeCheckCompute().handle(
        ModelCanonicalFileShapeCheckInput(
            facts=ModelCanonicalFileShapeFacts.model_validate(
                {"head_tree": {"files": []}}
            ),
            contract=invalid,
        )
    )
    assert report.overall_status == "ERROR"


def test_rule_severity_comes_from_the_contract_row() -> None:
    rules = RULES.model_copy(
        update={"severities": {**RULES.severities, "noncanonical-file": "warning"}}
    )
    issues = check(_facts("violation_noncanonical-file.json"), rules)
    assert [i.severity for i in issues] == [EnumSeverity.WARNING]


# --- every parameters key changes a verdict ------------------------------------


def _tree(files: list[str], **kw: Any) -> dict[str, Any]:
    return {"files": files, **kw}


def _inline(**kw: Any) -> ModelCanonicalFileShapeFacts:
    return ModelCanonicalFileShapeFacts.model_validate(kw)


PRE_COMMIT_CORE = (
    "repos:\n"
    "  - repo: https://github.com/OmniNode-ai/omnibase_core\n"
    "    rev: v1\n"
    "    hooks:\n"
    "      - id: check-direct-model-call\n"
    "        args: ['--baseline', 'config/dm_baseline.yaml']\n"
)
PRE_COMMIT_LOCAL = (
    "repos:\n"
    "  - repo: local\n"
    "    hooks:\n"
    "      - id: check-direct-model-call\n"
    "        entry: python -m tools.dm\n"
    "        args: ['--baseline', 'config/dm_baseline.yaml']\n"
)
MANIFEST = "- id: check-direct-model-call\n  entry: python -m tools.dm\n"
PRE_COMMIT_NODE_BOUNDARY = (
    "repos:\n"
    "  - repo: https://github.com/OmniNode-ai/omnibase_core\n"
    "    hooks:\n"
    "      - id: check-node-boundary-imports\n"
)
PRE_COMMIT_MODEL_CONFIG = (
    "repos:\n"
    "  - repo: https://github.com/OmniNode-ai/omnibase_core\n"
    "    hooks:\n"
    "      - id: check-hardcoded-model-config-compute\n"
)
WORKFLOW_GUARD = (
    "jobs:\n"
    "  guard:\n"
    "    uses: OmniNode-ai/omnibase_core/.github/workflows/imperative-contract-guard.yml@abc\n"
    "    with:\n"
    "      allowlist-path: config/guard_allowlist.yaml\n"
)


def _declared(
    added: str, config: str, manifest: str | None = None, workflow: str | None = None
) -> ModelCanonicalFileShapeFacts:
    texts = [{"path": ".pre-commit-config.yaml", "text": config}]
    if manifest is not None:
        texts.append({"path": ".pre-commit-hooks.yaml", "text": manifest})
    if workflow is not None:
        texts.append({"path": ".github/workflows/g.yml", "text": workflow})
    return _inline(
        head_tree=_tree([added]),
        has_base=True,
        declared_texts=texts,
        changes=[{"status": "A", "path": added, "new_text": "- a\n"}],
    )


BURNDOWN_HEADER = "# Burn-down ticket: OMN-21521 compat file-shape findings\n"
BURNDOWN_FILE = ".onex_ratchets/canonical_file_shape_burndown_baseline.txt"

SCENARIOS: dict[str, Callable[[], ModelCanonicalFileShapeFacts]] = {
    "burndown_installed": lambda: _facts("clean_burndown-ticket-missing.json"),
    "burndown_ticket_missing": lambda: _facts("violation_burndown-ticket-missing.json"),
    "burndown_removed": lambda: _facts("violation_burndown-baseline-removed.json"),
    "burndown_file_added": lambda: _inline(
        head_tree=_tree(["scripts/new.py", BURNDOWN_FILE]),
        has_base=True,
        head_burndown_text=BURNDOWN_HEADER + "scripts/new.py\n",
        changes=[
            {
                "status": "A",
                "path": BURNDOWN_FILE,
                "new_text": BURNDOWN_HEADER + "scripts/new.py\n",
            }
        ],
    ),
    "burndown_stale": lambda: _inline(
        head_tree=_tree([]),
        has_base=True,
        head_burndown_text=BURNDOWN_HEADER + "scripts/gone.py\n",
    ),
    "burndown_extra_added": lambda: _facts("violation_burndown-extra-entry.json"),
    "burndown_modified": lambda: _facts("clean_burndown-extra-entry.json"),
    "burndown_extra_duplicate": lambda: _inline(
        head_tree=_tree(["scripts/new.py"]),
        has_base=True,
        head_baseline_text="scripts/new.py\n",
        head_burndown_text=BURNDOWN_HEADER + "scripts/new.py\n",
    ),
    "burndown_ticket_uncited": lambda: _facts("violation_burndown-ticket-uncited.json"),
    "burndown_ticket_cited": lambda: _facts("clean_burndown-ticket-uncited.json"),
    "burndown_growth": lambda: _inline(
        head_tree=_tree(["scripts/new.py"]),
        has_base=True,
        base_burndown_text=BURNDOWN_HEADER,
        head_burndown_text=BURNDOWN_HEADER + "scripts/new.py\n",
    ),
    "noncanonical": lambda: _facts("violation_noncanonical-file.json"),
    "canonical_nodes": lambda: _facts("clean_noncanonical-file.json"),
    "canonical_validation": lambda: _inline(
        head_tree=_tree(["src/pkg/validation/checker_a.py"])
    ),
    "canonical_tests": lambda: _inline(head_tree=_tree(["tests/unit/test_a.py"])),
    "canonical_docs": lambda: _inline(head_tree=_tree(["docs/a.py"])),
    "canonical_conftest": lambda: _inline(head_tree=_tree(["conftest.py"])),
    "shebang": lambda: _inline(
        head_tree=_tree(
            ["tools/run"],
            shebang_lines=[{"path": "tools/run", "text": "#!/usr/bin/env python3"}],
        )
    ),
    "shell": lambda: _inline(head_tree=_tree(["tools/a.sh"])),
    "node_home_baseline": lambda: _inline(
        head_tree=_tree([".onex_ratchets/node_home_baseline.txt"]),
        has_base=True,
        changes=[
            {
                "status": "A",
                "path": ".onex_ratchets/node_home_baseline.txt",
                "new_text": "a\n",
            }
        ],
    ),
    "baseline_stale": lambda: _facts("violation_baseline-stale.json"),
    "baseline_growth": lambda: _facts("violation_baseline-growth.json"),
    "baselined_growth": lambda: _facts("violation_baselined-file-growth.json"),
    "baselined_comment_growth": lambda: _inline(
        head_tree=_tree(["scripts/old.py"]),
        has_base=True,
        head_baseline_text="scripts/old.py\n",
        base_baseline_text="scripts/old.py\n",
        changes=[
            {
                "status": "M",
                "path": "scripts/old.py",
                "new_text": "a = 1\n# c\n# d\n",
                "old_text": "a = 1\n",
            }
        ],
    ),
    "skill": lambda: _facts("violation_skill-imperative.json"),
    "suppression": lambda: _facts("violation_suppression-growth.json"),
    "suppression_yaml": lambda: _inline(
        head_tree=_tree(["config/x.yaml"]),
        has_base=True,
        changes=[
            {
                "status": "M",
                "path": "config/x.yaml",
                "new_text": f"a: 1  {NOQA}\n",
                "old_text": "a: 1\n",
            }
        ],
    ),
    "new_exception": lambda: _facts("violation_new-exception-file.json"),
    "prose_baseline": lambda: _inline(
        head_tree=_tree(["docs/baseline_notes.md"]),
        has_base=True,
        changes=[
            {"status": "A", "path": "docs/baseline_notes.md", "new_text": "notes\n"}
        ],
    ),
    "exception_growth": lambda: _facts("violation_exception-entry-growth.json"),
    "declared_core": lambda: _declared("config/dm_baseline.yaml", PRE_COMMIT_CORE),
    "declared_local": lambda: _declared(
        "config/dm_baseline.yaml", PRE_COMMIT_LOCAL, MANIFEST
    ),
    "declared_node_boundary": lambda: _declared(
        ".onex_ratchets/node_boundary_import_baseline.yaml", PRE_COMMIT_NODE_BOUNDARY
    ),
    "declared_model_config": lambda: _declared(
        "config/hardcoded_model_config_baseline.yaml", PRE_COMMIT_MODEL_CONFIG
    ),
    "declared_guard": lambda: _declared(
        "config/guard_allowlist.yaml", "repos: []\n", None, WORKFLOW_GUARD
    ),
    "no_code": lambda: _facts("violation_lifecycle-no-code.json"),
    "fix_only_new": lambda: _facts("violation_lifecycle-fix-only-new-file.json"),
    "fix_only_growth": lambda: _facts("violation_lifecycle-fix-only-growth.json"),
    "fix_only_stamped": lambda: _facts("clean_lifecycle-fix-only-growth.json"),
    "retired": lambda: _facts("violation_lifecycle-retired.json"),
    "bad_state": lambda: _lifecycle("sleeping", [_change("docs/a.md", "x\n", "y\n")]),
    "handler": lambda: _facts("violation_handler_outside_node.json"),
    "handler_bound": lambda: _facts("clean_handler_outside_node.json"),
    "handler_default_bound": lambda: _inline(
        head_tree=_tree(
            ["src/pkg/nodes/node_z/handler_z.py", "src/pkg/nodes/node_z/contract.yaml"],
            contract_texts=[
                {
                    "path": "src/pkg/nodes/node_z/contract.yaml",
                    "text": "handler_routing:\n  default_handler: handler_z:HandlerZ\n",
                }
            ],
        )
    ),
    "cli": lambda: _facts("violation_cli_entry_outside_node.json"),
    "cli_runtime": lambda: _facts("clean_cli_entry_outside_node.json"),
    "cli_script_only": lambda: _inline(
        head_tree=_tree(
            ["src/pkg/handlers/handler_y.py", "src/pkg/nodes/node_y/contract.yaml"],
            contract_texts=[
                {
                    "path": "src/pkg/nodes/node_y/contract.yaml",
                    "text": "handler:\n  module: pkg.handlers.handler_y\n",
                }
            ],
            pyproject_text='[project.scripts]\ny = "pkg.handlers.handler_y:main"\n',
        )
    ),
}

# parameters key -> (scenario that the key controls, inert replacement value)
INERT_STR = "zz-mutated"
MUTATIONS: dict[str, tuple[str, object]] = {
    "code_extensions": ("noncanonical", ()),
    "canonical_src_dirs": ("canonical_nodes", ()),
    "canonical_prefixed_dirs": ("canonical_validation", ()),
    "test_dirs": ("canonical_tests", ()),
    "docs_root": ("canonical_docs", INERT_STR),
    "always_canonical_names": ("canonical_conftest", ()),
    "src_root": ("canonical_nodes", INERT_STR),
    "shebang_prefix": ("shebang", INERT_STR),
    "canonical_src_min_parts": ("canonical_nodes", 99),
    "noncanonical_text": ("noncanonical", INERT_STR),
    "shell_text": ("shell", INERT_STR),
    "baseline_path": ("baseline_stale", INERT_STR),
    "node_home_baseline_path": ("node_home_baseline", INERT_STR),
    "baseline_stale_text": ("baseline_stale", INERT_STR),
    "baseline_growth_text": ("baseline_growth", INERT_STR),
    "burndown_baseline_path": ("burndown_file_added", INERT_STR),
    "burndown_ticket_pattern": ("burndown_installed", INERT_STR),
    "burndown_ticket_missing_text": ("burndown_ticket_missing", INERT_STR),
    "burndown_stale_text": ("burndown_stale", INERT_STR),
    "burndown_growth_text": ("burndown_growth", INERT_STR),
    "burndown_removed_text": ("burndown_removed", INERT_STR),
    "burndown_base_statuses": ("burndown_modified", ()),
    "burndown_extra_added_text": ("burndown_extra_added", INERT_STR),
    "burndown_extra_duplicate_text": ("burndown_extra_duplicate", INERT_STR),
    "burndown_ticket_id_pattern": ("burndown_ticket_uncited", INERT_STR),
    "burndown_ticket_citation_pattern": ("burndown_ticket_cited", INERT_STR),
    "burndown_ticket_uncited_text": ("burndown_ticket_uncited", INERT_STR),
    "comment_prefixes": ("baselined_comment_growth", ()),
    "baselined_growth_text": ("baselined_growth", INERT_STR),
    "skill_file_name": ("skill", INERT_STR),
    "imperative_patterns": ("skill", ()),
    "skill_imperative_text": ("skill", INERT_STR),
    "suppression_patterns": ("suppression", ()),
    "config_extensions": ("suppression_yaml", ()),
    "suppression_growth_text": ("suppression", INERT_STR),
    "exception_name_pattern": ("new_exception", INERT_STR),
    "prose_extensions": ("prose_baseline", ()),
    "new_exception_text": ("new_exception", INERT_STR),
    "exception_growth_text": ("exception_growth", INERT_STR),
    "pre_commit_config_path": ("declared_core", INERT_STR),
    "hooks_manifest_path": ("declared_local", INERT_STR),
    "workflows_dir": ("declared_guard", INERT_STR),
    "gate_hook_ids": ("declared_core", ()),
    "node_boundary_hook_name": ("declared_node_boundary", INERT_STR),
    "node_boundary_baseline": ("declared_node_boundary", INERT_STR),
    "model_config_hook_name": ("declared_model_config", INERT_STR),
    "model_config_baseline": ("declared_model_config", INERT_STR),
    "gate_repo_url_pattern": ("declared_core", INERT_STR),
    "guard_workflow_uses_pattern": ("declared_guard", INERT_STR),
    "guard_allowlist_input": ("declared_guard", INERT_STR),
    "lifecycle_path": ("bad_state", INERT_STR),
    "lifecycle_state_key": ("no_code", INERT_STR),
    "lifecycle_states": ("no_code", ()),
    "no_code_state": ("no_code", INERT_STR),
    "fix_only_state": ("fix_only_new", INERT_STR),
    "retired_state": ("retired", INERT_STR),
    "release_trailer_key": ("fix_only_stamped", INERT_STR),
    "no_code_text": ("no_code", INERT_STR),
    "fix_only_new_file_text": ("fix_only_new", INERT_STR),
    "fix_only_growth_text": ("fix_only_growth", INERT_STR),
    "retired_text": ("retired", INERT_STR),
    "handler_file_prefix": ("handler", INERT_STR),
    "contract_file_name": ("handler_bound", INERT_STR),
    "binding_handler_key": ("handler_bound", INERT_STR),
    "binding_module_key": ("handler_bound", INERT_STR),
    "binding_default_key": ("handler_default_bound", INERT_STR),
    "handler_outside_node_text": ("handler", INERT_STR),
    "node_runtime_prefix": ("cli_runtime", INERT_STR),
    "scripts_key_path": ("cli_script_only", INERT_STR),
    "cli_entry_outside_node_text": ("cli", INERT_STR),
}
# Read from the repository by the node runtime (git facts), not by the checker; the
# runtime test mutates these through a fixture repository. The node-home keys and
# the git-reader ceiling are mutated in test_node_home_admission.py; target_branch_refs in
# test_index_base_is_merge_base.py.
READER_KEYS = frozenset(
    {
        "handler_class_pattern",
        "argparse_pattern",
        "main_pattern",
        "cat_file_timeout_s",
        "target_branch_refs",
        "baseline_header",
        "burndown_baseline_header",
    }
) | {
    key
    for key in ModelCanonicalFileShapeRules.model_fields
    if key.startswith("node_home_")
} - {"node_home_baseline_path"}


def test_every_parameter_key_is_mutated_by_a_table_row() -> None:
    declared = set(ModelCanonicalFileShapeRules.model_fields)
    assert declared == set(MUTATIONS) | READER_KEYS
    in_contract = {key for rule in CONTRACT.rules for key in (rule.parameters or {})}
    assert in_contract == declared


@pytest.mark.parametrize("key", sorted(MUTATIONS))
def test_mutating_a_parameter_changes_the_verdict_of_its_scenario(key: str) -> None:
    scenario, inert = MUTATIONS[key]
    facts = SCENARIOS[scenario]()
    before = _messages(facts)
    mutated = RULES.model_copy(
        update={"parameters": RULES.parameters.model_copy(update={key: inert})}
    )
    after = _messages(facts, mutated)
    assert before != after, f"{key} does not control the {scenario} scenario"


def test_the_fixture_files_are_valid_json_facts() -> None:
    for path in [*FIXTURES.glob("violation_*.json"), *FIXTURES.glob("clean_*.json")]:
        ModelCanonicalFileShapeFacts.model_validate(json.loads(path.read_text()))


def test_a_test_data_file_named_like_an_exception_list_is_not_one() -> None:
    """Rule data under tests/ (a fixture named after a rule) is not an exception file."""
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {"files": ["tests/fixtures/x/violation_baseline-growth.json"]},
            "has_base": True,
            "changes": [
                {
                    "status": "A",
                    "path": "tests/fixtures/x/violation_baseline-growth.json",
                    "new_text": "{}\n",
                },
                {"status": "A", "path": "config/x_baseline.yaml", "new_text": "- a\n"},
            ],
        }
    )
    assert [str(i.file_path) for i in check(facts, RULES)] == ["config/x_baseline.yaml"]
