# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""omnimarket validator residency ratchet (OMN-21503, plan task T-Q6).

Fixture trees stand in for omnimarket; the checker is pure over the supplied
listing, so none of these tests needs a sibling clone.
"""

import ast
from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_validator_inventory_class import (
    EnumValidatorInventoryClass,
)
from omnibase_core.enums.enum_validator_inventory_kind import (
    EnumValidatorInventoryKind,
)
from omnibase_core.handlers import handler_omnimarket_validator_residency as checker
from omnibase_core.models.validation.model_omnimarket_validator_inventory_entry import (
    ModelOmnimarketValidatorInventoryEntry,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_policy import (
    ModelOmnimarketValidatorResidencyPolicy,
)

SCRIPT_A = "scripts/ci/check_alpha.py"
SCRIPT_B = "scripts/ci/check_beta.py"
NODE_V = "src/omnimarket/nodes/node_gamma_validate_compute"
NODE_D = "src/omnimarket/nodes/node_delta_gate_compute"


def _policy(**overrides: object) -> ModelOmnimarketValidatorResidencyPolicy:
    base: dict[str, object] = {
        "script_globs": ("scripts/ci/check_*", "scripts/validation/validate_*"),
        "node_root": "src/omnimarket/nodes",
        "node_name_patterns": (r"node_.*_validate_.*", r"node_.*_gate_.*"),
        "child_ticket_severity": EnumSeverity.WARNING,
        "acceptance_wave": 4,
        "wave_obligation": "omnimarket_validator_baseline_zero",
    }
    base.update(overrides)
    return ModelOmnimarketValidatorResidencyPolicy.model_validate(base)


def _entry(
    ident: str,
    cls: EnumValidatorInventoryClass,
    *,
    kind: EnumValidatorInventoryKind = EnumValidatorInventoryKind.SCRIPT,
    replacing: str | None = "checker_x",
    ticket: str | None = "OMN-1",
) -> ModelOmnimarketValidatorInventoryEntry:
    return ModelOmnimarketValidatorInventoryEntry(
        path=ident,
        kind=kind,
        validator_class=cls,
        replacing_core_validator=replacing,
        child_ticket=ticket,
    )


V = EnumValidatorInventoryClass.VALIDATOR
D = EnumValidatorInventoryClass.DECISION
NODE = EnumValidatorInventoryKind.NODE

INVENTORY = (
    _entry(SCRIPT_A, V),
    _entry(SCRIPT_B, V),
    _entry(NODE_V, V, kind=NODE),
    _entry(NODE_D, D, kind=NODE, replacing=None, ticket=None),
)
TREE = (
    SCRIPT_A,
    SCRIPT_B,
    "scripts/ci/not_a_check.py",
    f"{NODE_V}/contract.yaml",
    f"{NODE_V}/handler.py",
    f"{NODE_D}/contract.yaml",
    "src/omnimarket/nodes/sweep_scope.py",
)
BASELINE = (SCRIPT_A, SCRIPT_B, NODE_V)


def _run(
    tree: tuple[str, ...] = TREE,
    inventory: tuple[ModelOmnimarketValidatorInventoryEntry, ...] = INVENTORY,
    baseline: tuple[str, ...] = BASELINE,
    previous: tuple[str, ...] | None = None,
    policy: ModelOmnimarketValidatorResidencyPolicy | None = None,
) -> checker.ModelOmnimarketValidatorResidencyResult:
    return checker.check_validator_residency(
        tree_paths=tree,
        policy=policy or _policy(),
        inventory=inventory,
        baseline_ids=baseline,
        previous_baseline_ids=previous,
    )


@pytest.mark.unit
class TestResidencyCount:
    def test_counts_validators_and_not_decisions(self) -> None:
        result = _run()
        assert result.resident_validators == (SCRIPT_A, SCRIPT_B, NODE_V)
        assert result.count == 3
        assert result.ok

    def test_a_new_check_script_fails(self) -> None:
        """The plan's failing test: a new scripts/ci/check_*.py passed `ci`."""
        tree = (*TREE, "scripts/ci/check_new_thing.py")
        result = _run(tree=tree)
        assert not result.ok
        assert "scripts/ci/check_new_thing.py" in result.unclassified
        codes = {issue.code for issue in result.issues}
        assert {"baseline_added", "inventory_unclassified"} <= codes

    def test_a_raised_baseline_fails(self) -> None:
        result = _run(
            baseline=(*BASELINE, "scripts/ci/check_gone.py"), previous=BASELINE
        )
        assert not result.ok
        assert "baseline_raised" in {issue.code for issue in result.issues}

    def test_a_shrunk_baseline_passes(self) -> None:
        tree = tuple(p for p in TREE if p != SCRIPT_B)
        inventory = tuple(e for e in INVENTORY if e.path != SCRIPT_B)
        result = _run(
            tree=tree,
            inventory=inventory,
            baseline=(SCRIPT_A, NODE_V),
            previous=BASELINE,
        )
        assert result.ok
        assert result.count == 2

    def test_a_stale_inventory_entry_fails(self) -> None:
        tree = tuple(p for p in TREE if p != SCRIPT_B)
        result = _run(tree=tree)
        assert "inventory_stale" in {issue.code for issue in result.issues}
        assert not result.ok

    def test_decision_node_stays_uncounted_when_unlisted_node_appears(self) -> None:
        tree = (*TREE, "src/omnimarket/nodes/node_epsilon_gate_effect/contract.yaml")
        result = _run(tree=tree)
        assert "src/omnimarket/nodes/node_epsilon_gate_effect" in result.unclassified
        assert not result.ok


@pytest.mark.unit
class TestInventoryCompleteness:
    def test_validator_without_replacement_fails(self) -> None:
        inventory = (_entry(SCRIPT_A, V, replacing=None), *INVENTORY[1:])
        result = _run(inventory=inventory)
        assert "inventory_no_replacement" in {i.code for i in result.issues}
        assert not result.ok

    def test_missing_child_ticket_follows_policy_severity(self) -> None:
        inventory = (_entry(SCRIPT_A, V, ticket=None), *INVENTORY[1:])
        lenient = _run(inventory=inventory)
        assert lenient.ok
        assert "inventory_no_child_ticket" in {i.code for i in lenient.issues}
        strict = _run(
            inventory=inventory,
            policy=_policy(child_ticket_severity=EnumSeverity.ERROR),
        )
        assert not strict.ok


@pytest.mark.unit
class TestConfiguration:
    def test_contract_path_changes_the_count(self) -> None:
        """AC5: a policy that adds a glob changes the count with no code change."""
        tree = (*TREE, "scripts/other/lint_extra.py")
        inventory = (*INVENTORY, _entry("scripts/other/lint_extra.py", V))
        base = _run(tree=tree, inventory=inventory, baseline=BASELINE)
        wider = _run(
            tree=tree,
            inventory=inventory,
            baseline=BASELINE,
            policy=_policy(script_globs=("scripts/ci/check_*", "scripts/other/lint_*")),
        )
        assert base.count == 3
        assert wider.count == 4

    def test_checker_source_holds_no_path_or_pattern_literal(self) -> None:
        tree = ast.parse(Path(checker.__file__).read_text(encoding="utf-8"))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
        }
        literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ]
        for text in literals:
            if text in {"/", "\\"}:  # path separators, not paths
                continue
            assert "/" not in text and "*" not in text, text
            assert "scripts" not in text and "node_" not in text, text


@pytest.mark.unit
class TestWaveAcceptance:
    def test_wave_four_rejected_while_baseline_nonzero(self) -> None:
        manifest = {
            "waves": {"4": {"obligations": ["omnimarket_validator_baseline_zero"]}}
        }
        issues = checker.check_wave_acceptance(
            manifest=manifest, baseline_ids=BASELINE, policy=_policy()
        )
        assert [i.code for i in issues] == ["wave_baseline_nonzero"]

    def test_wave_four_without_the_obligation_is_rejected(self) -> None:
        manifest = {"waves": {"4": {"obligations": []}}}
        issues = checker.check_wave_acceptance(
            manifest=manifest, baseline_ids=(), policy=_policy()
        )
        assert [i.code for i in issues] == ["wave_obligation_missing"]

    def test_wave_four_accepted_at_zero_with_obligation(self) -> None:
        manifest = {
            "waves": {"4": {"obligations": ["omnimarket_validator_baseline_zero"]}}
        }
        assert (
            checker.check_wave_acceptance(
                manifest=manifest, baseline_ids=(), policy=_policy()
            )
            == ()
        )


@pytest.mark.unit
class TestBindings:
    def test_results_are_byte_identical(self) -> None:
        first = _run().canonical_json()
        second = _run(tree=tuple(reversed(TREE))).canonical_json()
        assert first == second
