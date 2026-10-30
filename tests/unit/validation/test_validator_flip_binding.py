# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The flip seam applies the generic rule data after resolving each binding."""

from pathlib import Path

import pytest

from omnibase_core.validation.validator_flip_binding import (
    classify_binding,
    classify_node,
    load_binding_document,
)
from omnibase_core.validation.validator_flip_scope import SCOPE
from omnibase_core.validation.validator_handler_shape import ValidatorHandlerShape
from scripts.ci.verify_flip_bundle import _classify_binding

pytestmark = pytest.mark.unit


def _handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str) -> Path:
    monkeypatch.setattr(SCOPE, "src_root", tmp_path)
    node = tmp_path / "pkg/nodes/node_x"
    node.mkdir(parents=True)
    (node / "handler_x.py").write_text(source, encoding="utf-8")
    contract = node / "contract.yaml"
    contract.write_text(
        "handler:\n  module: pkg.nodes.node_x.handler_x\n  class: HandlerX\n",
        encoding="utf-8",
    )
    return contract


@pytest.mark.parametrize(
    ("source", "rule_id"),
    [
        (
            "class HandlerX:\n    def handle(self, probes, pins, local_backends): ...\n",
            "noncanonical_handle",
        ),
        ("def run(request): ...\n", "module_function_handler"),
        (
            "class HandlerX:\n    def handle(self, request): return ModelEventEnvelope\n",
            "envelope_in_core",
        ),
        (
            "class HandlerX:\n    def handle(self, request): ...\n"
            "    def warm(self): self.state = 1\n",
            "mutating_public_method",
        ),
    ],
)
def test_flipped_binding_uses_every_generic_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str, rule_id: str
) -> None:
    contract = _handler(tmp_path, monkeypatch, source)
    finding = classify_node(contract)
    assert not finding.is_canonical
    assert finding.category == rule_id
    for classify in (classify_binding, _classify_binding):
        ok, detail = classify(
            "pkg.nodes.node_x.handler_x", "HandlerX", "pkg.nodes.node_x"
        )
        assert not ok
        assert rule_id in detail


def test_binding_reads_the_loaded_rule_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = _handler(
        tmp_path, monkeypatch, "class HandlerX:\n    def handle(self, injected): ...\n"
    )
    assert not classify_node(contract).is_canonical
    original = ValidatorHandlerShape().contract
    changed = original.model_copy(
        update={
            "rules": [
                rule.model_copy(
                    update={
                        "parameters": {
                            **rule.parameters,
                            "magic_param_names": ["injected"],
                        }
                    }
                )
                if rule.rule_id == "noncanonical_handle"
                else rule
                for rule in original.rules
            ]
        }
    )
    monkeypatch.setattr(
        ValidatorHandlerShape, "contract", property(lambda self: changed)
    )
    assert classify_node(contract).is_canonical


@pytest.mark.parametrize("reexport", [False, True])
def test_mutating_inherited_handler_is_refused_through_reexports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reexport: bool
) -> None:
    contract = _handler(
        tmp_path,
        monkeypatch,
        "from pkg.shared import Parent\nclass HandlerX(Parent):\n"
        "    def warm(self): self.state = 1\n",
    )
    (tmp_path / "pkg/shared.py").write_text(
        "class Parent:\n    def handle(self, request): ...\n", encoding="utf-8"
    )
    if reexport:
        (contract.parent / "export.py").write_text(
            "from pkg.nodes.node_x.handler_x import HandlerX\n", encoding="utf-8"
        )
        contract.write_text(
            "handler:\n  module: pkg.nodes.node_x.export\n  class: HandlerX\n",
            encoding="utf-8",
        )
    finding = classify_node(contract)
    assert not finding.is_canonical
    assert finding.category == "mutating_public_method"


@pytest.mark.parametrize("document", ["null", "a scalar", "[a, b]"])
def test_binding_loader_preserves_non_mapping_outcome(document: str) -> None:
    assert load_binding_document(document) is None


def test_binding_loader_keeps_unrelated_contract_fields() -> None:
    assert load_binding_document("handler_id: x\nforeign_metadata: [a, b]\n") == {
        "handler_id": "x",
        "foreign_metadata": ["a", "b"],
    }


@pytest.mark.parametrize("bound", [False, True])
def test_unparseable_handler_keeps_the_structural_missing_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: bool
) -> None:
    contract = _handler(tmp_path, monkeypatch, "not valid python!")
    if not bound:
        contract.write_text("name: node_x\n", encoding="utf-8")
    finding = classify_node(contract)
    assert not finding.is_canonical
    assert finding.category == ("phantom" if bound else "no_binding")
