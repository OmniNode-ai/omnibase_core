# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The canonical validator shape and the rule handler binding (OMN-21494).

A validator is the generic compute node: pure, rules as data, a handler bound through the
contract for a rule that cannot be data. Each refusal has a control: a node that breaks that
one property and is refused by that one rule. The control for I/O is a validator whose
compute step runs a process.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_rule_handler import resolve_rule_handler
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_validator_shape import ValidatorValidatorShape

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEAN_HANDLER = (
    "class NodeXCheckCompute:\n    def handle(self, request):\n        return request\n"
)
IO_HANDLER = (
    "import subprocess\n\n\nclass NodeXCheckCompute:\n    def handle(self, request):\n"
    "        return subprocess.run(['git', 'status'], check=False)\n"
)


def _node(
    root: Path,
    *,
    tag: str = "validator_node",
    node_type: str = "compute",
    purity: str = "pure",
    bound: bool = True,
    handler: str = CLEAN_HANDLER,
) -> Path:
    node = root / "node_x_check_compute"
    node.mkdir()
    lines = [
        "name: node_x_check_compute",
        f"node_type: {node_type}",
        f"tags: [{tag}]",
        "descriptor:",
        f"  purity: {purity}",
    ]
    if bound:
        lines += ["handler_routing:", "  default_handler: handler:NodeXCheckCompute"]
    (node / "contract.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (node / "handler.py").write_text(handler, encoding="utf-8")
    return node / "contract.yaml"


def _codes(contract: Path) -> list[str]:
    return sorted(
        i.code or "" for i in ValidatorValidatorShape().validate(contract).issues
    )


def test_a_pure_compute_validator_with_a_bound_handler_is_canonical(
    tmp_path: Path,
) -> None:
    assert _codes(_node(tmp_path)) == []


def test_an_effect_validator_is_refused_as_not_the_validator(tmp_path: Path) -> None:
    contract = _node(tmp_path, node_type="effect", purity="side_effecting")
    assert _codes(contract) == ["validator_node_archetype", "validator_node_impure"]


def test_a_validator_that_declares_itself_impure_is_refused(tmp_path: Path) -> None:
    assert _codes(_node(tmp_path, purity="side_effecting")) == ["validator_node_impure"]


def test_a_validator_whose_handler_no_contract_binds_is_refused(tmp_path: Path) -> None:
    assert _codes(_node(tmp_path, bound=False)) == ["validator_handler_unbound"]


def test_a_validator_that_does_io_in_its_compute_step_is_refused(
    tmp_path: Path,
) -> None:
    """The failing control: the same node with a process run in its handler is refused."""
    assert set(_codes(_node(tmp_path, handler=IO_HANDLER))) == {
        "validator_compute_step_io"
    }


def test_declaring_effect_does_not_hide_io_in_the_compute_step(tmp_path: Path) -> None:
    contract = _node(tmp_path, node_type="effect", handler=IO_HANDLER)
    assert "validator_compute_step_io" in _codes(contract)


def test_the_effect_around_a_validator_is_not_judged_as_the_validator(
    tmp_path: Path,
) -> None:
    contract = _node(
        tmp_path,
        tag="validator_support_node",
        node_type="effect",
        purity="side_effecting",
        handler=IO_HANDLER,
    )
    assert _codes(contract) == []


def test_a_node_that_is_not_tagged_a_validator_is_not_judged(tmp_path: Path) -> None:
    assert _codes(_node(tmp_path, tag="other", node_type="effect")) == []


def test_the_required_node_type_is_data_not_code(tmp_path: Path) -> None:
    contract = _node(tmp_path, node_type="effect")
    base = ValidatorValidatorShape().contract
    rules = [
        r.model_copy(update={"parameters": {"required_node_type": "effect"}})
        if r.rule_id == "validator_node_archetype"
        else r
        for r in base.rules
    ]
    changed = ModelValidatorSubcontract(
        **{**base.model_dump(), "rules": [r.model_dump() for r in rules]}
    )
    issues = ValidatorValidatorShape(contract=changed).validate(contract).issues
    assert "validator_node_archetype" not in {i.code for i in issues}


def test_core_validator_nodes_are_judged_and_the_compute_ones_are_canonical() -> None:
    nodes = REPO_ROOT / "src/omnibase_core/nodes"
    validator = ValidatorValidatorShape()
    refused: set[str] = set()
    for contract in sorted(nodes.glob("*/contract.yaml")):
        if any(i.code for i in validator.validate(contract).issues):
            refused.add(contract.parent.name)
    assert "node_canonical_file_shape_check_compute" not in refused
    assert "node_no_hardcoded_topics_check_compute" not in refused
    assert (
        "node_todo_format_check_effect" in refused
    )  # an effect that holds its own check


# --- a rule that cannot be data is a handler bound through the contract -------------------


def test_a_rule_names_its_handler_and_the_binding_resolves() -> None:
    rule = ModelValidatorRule(rule_id="r", description="d", handler="os.path:basename")
    resolved = resolve_rule_handler(rule)
    assert resolved is not None
    assert resolved("a/b") == "b"


def test_a_rule_with_no_handler_is_judged_by_its_parameters_alone() -> None:
    assert (
        resolve_rule_handler(ModelValidatorRule(rule_id="r", description="d")) is None
    )


@pytest.mark.parametrize(
    "reference", ["/tmp/x.py", "os.path", "a b:c", "os.path:", ":x"]
)
def test_a_handler_reference_that_is_not_module_and_name_is_refused(
    reference: str,
) -> None:
    with pytest.raises(ValueError, match="handler"):
        ModelValidatorRule(rule_id="r", description="d", handler=reference)


@pytest.mark.parametrize("reference", ["no_such_module_zz:fn", "os.path:no_such_name"])
def test_a_handler_that_does_not_resolve_fails_the_load(reference: str) -> None:
    rule = ModelValidatorRule(rule_id="r", description="d", handler=reference)
    with pytest.raises(ModelOnexError, match="binds handler"):
        resolve_rule_handler(rule)


def test_the_generic_validator_hands_back_the_handler_a_rule_is_bound_to() -> None:
    contract = ModelValidatorSubcontract.model_validate(
        {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "validator_id": "t",
            "validator_name": "t",
            "validator_description": "t",
            "target_patterns": ["**/*"],
            "rules": [
                {"rule_id": "bound", "description": "d", "handler": "os.path:basename"},
                {"rule_id": "plain", "description": "d"},
            ],
        }
    )

    class Probe(ValidatorBase):
        validator_id = "t"

        def _validate_file(
            self, path: Path, contract: ModelValidatorSubcontract
        ) -> tuple[ModelValidationIssue, ...]:
            return ()

    probe = Probe(contract=contract)
    assert probe.rule_handler("bound") is not None
    assert probe.rule_handler("plain") is None
    assert probe.rule_handler("absent") is None
