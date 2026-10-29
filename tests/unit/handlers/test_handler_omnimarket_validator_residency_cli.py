# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Entry, packaged inventory and baseline of the residency ratchet (OMN-21503)."""

from pathlib import Path

import pytest

from omnibase_core.enums.enum_validator_inventory_class import (
    EnumValidatorInventoryClass,
)
from omnibase_core.handlers.handler_hardcoded_threshold import load_packaged_contract
from omnibase_core.handlers.handler_omnimarket_validator_residency import (
    check_validator_residency,
    check_wave_acceptance,
    discover_residents,
)
from omnibase_core.handlers.handler_omnimarket_validator_residency_cli import (
    check_tree,
    derive_baseline,
    load_baseline,
    load_inventory,
    main,
    policy_from_contract,
)

_PACKAGE = Path(__file__).parents[3] / "src" / "omnibase_core" / "validation"
INVENTORY_FILE = _PACKAGE / "inventory" / "omnimarket_validator_inventory.yaml"


def _baseline() -> tuple[str, ...]:
    return derive_baseline(load_inventory(INVENTORY_FILE))


def _materialize(root: Path, rel_paths: tuple[str, ...]) -> None:
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")


def _inventory_tree() -> tuple[str, ...]:
    """A tree holding exactly the files the packaged inventory names."""
    paths: list[str] = []
    for entry in load_inventory(INVENTORY_FILE):
        if entry.kind.value == "node":
            paths.append(f"{entry.path}/contract.yaml")
        else:
            paths.append(entry.path)
    return tuple(paths)


@pytest.mark.unit
class TestPackagedInventory:
    def test_inventory_matches_a_tree_of_its_own_files(self) -> None:
        """AC1: the inventory and the files under the scanned paths agree."""
        contract = load_packaged_contract("omnimarket_validator_residency")
        residents = dict(
            discover_residents(_inventory_tree(), policy_from_contract(contract))
        )
        assert set(residents) == {e.path for e in load_inventory(INVENTORY_FILE)}

    def test_every_validator_entry_names_a_replacement(self) -> None:
        for entry in load_inventory(INVENTORY_FILE):
            if entry.validator_class is EnumValidatorInventoryClass.VALIDATOR:
                assert entry.replacing_core_validator, entry.path

    def test_emitted_baseline_round_trips_and_is_the_validator_entries(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--emit-baseline"]) == 0
        emitted = tmp_path / "baseline.yaml"
        emitted.write_text(capsys.readouterr().out, encoding="utf-8")
        validators = sorted(
            e.path
            for e in load_inventory(INVENTORY_FILE)
            if e.validator_class is EnumValidatorInventoryClass.VALIDATOR
        )
        assert list(load_baseline(emitted)) == validators
        assert len(set(validators)) == len(validators)

    def test_the_committed_tree_passes_and_only_lacks_child_tickets(self) -> None:
        contract = load_packaged_contract("omnimarket_validator_residency")
        result = check_validator_residency(
            tree_paths=_inventory_tree(),
            policy=policy_from_contract(contract),
            inventory=load_inventory(INVENTORY_FILE),
            baseline_ids=_baseline(),
        )
        assert result.ok
        assert {i.code for i in result.issues} <= {"inventory_no_child_ticket"}

    def test_wave_four_is_rejected_by_the_committed_baseline(self) -> None:
        policy = policy_from_contract(
            load_packaged_contract("omnimarket_validator_residency")
        )
        manifest = {"waves": {"4": {"obligations": [policy.wave_obligation]}}}
        issues = check_wave_acceptance(
            manifest=manifest,
            baseline_ids=_baseline(),
            policy=policy,
        )
        assert [i.code for i in issues] == ["wave_baseline_nonzero"]


@pytest.mark.unit
class TestEntryParity:
    def test_entry_and_pure_checker_are_byte_identical(self, tmp_path: Path) -> None:
        """AC6: the I/O entry and the pure checker over the same listing agree."""
        tree = (*_inventory_tree(), "README.md")
        _materialize(tmp_path, tree)
        contract = load_packaged_contract("omnimarket_validator_residency")
        via_entry = check_tree(tmp_path).canonical_json()
        direct = check_validator_residency(
            tree_paths=tree,
            policy=policy_from_contract(contract),
            inventory=load_inventory(INVENTORY_FILE),
            baseline_ids=_baseline(),
        ).canonical_json()
        assert via_entry == direct

    def test_check_tree_reports_a_new_check_script(self, tmp_path: Path) -> None:
        tree = (*_inventory_tree(), "scripts/ci/check_brand_new.py")
        _materialize(tmp_path, tree)
        result = check_tree(tmp_path)
        assert not result.ok
        assert "baseline_added" in {i.code for i in result.issues}

    def test_main_exit_codes(self, tmp_path: Path) -> None:
        _materialize(tmp_path, _inventory_tree())
        assert main([str(tmp_path)]) == 0
        _materialize(tmp_path, ("scripts/ci/check_brand_new.py",))
        assert main([str(tmp_path)]) == 1

    def test_main_fails_a_raised_baseline(self, tmp_path: Path) -> None:
        _materialize(tmp_path, _inventory_tree())
        previous = tmp_path / "previous.yaml"
        ids = _baseline()
        previous.write_text(
            "schema_version: 1\nresident_validators:\n"
            + "".join(f"  - {i}\n" for i in ids[1:]),
            encoding="utf-8",
        )
        assert main([str(tmp_path), "--previous-baseline", str(previous)]) == 1
