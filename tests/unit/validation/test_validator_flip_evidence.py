# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Binding, scope and receipt behavior retained after the checker migration."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from omnibase_core.models.flip_bundle.model_parity_verdict import ModelParityVerdict
from omnibase_core.validation import validator_flip_artifacts as artifacts
from omnibase_core.validation import validator_flip_binding as bindings
from omnibase_core.validation import validator_flip_parity as parity
from omnibase_core.validation import validator_flip_receipts as receipts
from omnibase_core.validation import validator_flip_scope as fscope

pytestmark = pytest.mark.unit


def test_contract_bindings_explicit_module() -> None:
    data = {"handler": {"module": "pkg.nodes.node_x.handlers.h", "class": "HandlerX"}}
    assert bindings._contract_bindings(data)[0] == (
        "pkg.nodes.node_x.handlers.h",
        "HandlerX",
    )


def test_contract_bindings_default_handler() -> None:
    data = {"handler_routing": {"default_handler": "handler:NodeX"}}
    module, cls = bindings._contract_bindings(data)[0]
    assert cls == "NodeX"
    assert module == ""  # no module in "handler:NodeX" — resolved from node package


def test_contract_bindings_default_handler_with_module() -> None:
    data = {"handler_routing": {"default_handler": "pkg.nodes.node_x.handler:NodeX"}}
    assert bindings._contract_bindings(data)[0] == ("pkg.nodes.node_x.handler", "NodeX")


def test_contract_bindings_none_when_handler_id_only() -> None:
    # handler_id-only contracts fall back to the node package at classify time.
    assert (
        bindings._contract_bindings({"handler_id": "node.x", "input_model": "pkg.M"})
        == []
    )


@pytest.mark.unit
@pytest.mark.parametrize("binding", ["named", "unnamed", "reexport"])
@pytest.mark.parametrize(
    "base_module", ["pkg.nodes.node_x.handlers.base", "pkg.shared.base"]
)
@pytest.mark.parametrize("relative_import", [False, True])
def test_inherited_handle_is_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: str,
    base_module: str,
    relative_import: bool,
) -> None:
    monkeypatch.setattr(fscope.SCOPE, "src_root", tmp_path)
    node = tmp_path / "pkg/nodes/node_x"
    handlers = node / "handlers"
    handlers.mkdir(parents=True)
    base = tmp_path / (base_module.replace(".", "/") + ".py")
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_text(
        "class HandlerBase:\n"
        "    async def handle(self, command: ModelCommand) -> ModelResult: ...\n",
        encoding="utf-8",
    )
    imported_module = base_module
    if relative_import:
        imported_module = ".base" if base.parent == handlers else "....shared.base"
    runtime = handlers / "runtime.py"
    runtime.write_text(
        f"from {imported_module} import HandlerBase as Parent\n"
        "class HandlerRuntime(Parent):\n"
        "    def __init__(self) -> None: ...\n",
        encoding="utf-8",
    )
    module = "pkg.nodes.node_x.handlers.runtime"
    class_binding = "  class: HandlerRuntime\n"
    if binding == "unnamed":
        class_binding = ""
    elif binding == "reexport":
        (handlers / "export.py").write_text(
            f"from {module} import HandlerRuntime as HandlerExport\n",
            encoding="utf-8",
        )
        module = "pkg.nodes.node_x.handlers.export"
        class_binding = "  class: HandlerExport\n"
    contract = node / "contract.yaml"
    contract.write_text(
        f"handler:\n  module: {module}\n{class_binding}", encoding="utf-8"
    )

    finding = bindings.classify_node(contract)

    assert finding.category == "canonical"
    assert finding.is_canonical
    fn, cls, path = bindings._resolve_handler(
        bindings._module_to_files(module),
        None if binding == "unnamed" else class_binding.split(": ")[1].strip(),
    )
    assert fn is not None
    assert cls is not None and cls.name == "HandlerBase"
    assert path == base


@pytest.mark.unit
@pytest.mark.parametrize("with_operation", [False, True])
def test_no_handle_in_ancestors_stays_noncanonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_operation: bool
) -> None:
    monkeypatch.setattr(fscope.SCOPE, "src_root", tmp_path)
    node = tmp_path / "pkg/nodes/node_x"
    node.mkdir(parents=True)
    (node / "base.py").write_text("class Base: ...\n", encoding="utf-8")
    (node / "handler.py").write_text(
        "from pkg.nodes.node_x.base import Base\n"
        "class HandlerRuntime(Base):\n"
        + ("    def execute(self, command): ...\n" if with_operation else "    pass\n"),
        encoding="utf-8",
    )
    contract = node / "contract.yaml"
    contract.write_text(
        "handler:\n  module: pkg.nodes.node_x.handler\n  class: HandlerRuntime\n",
        encoding="utf-8",
    )

    finding = bindings.classify_node(contract)

    assert finding.category == ("op_method" if with_operation else "empty")
    assert not finding.is_canonical


@pytest.mark.unit
@pytest.mark.parametrize("direct_handle", [False, True])
def test_inherited_handle_checks_defining_module_for_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, direct_handle: bool
) -> None:
    monkeypatch.setattr(fscope.SCOPE, "src_root", tmp_path)
    node = tmp_path / "pkg/nodes/node_x"
    node.mkdir(parents=True)
    (node / "base.py").write_text(
        "from elsewhere import ModelEventEnvelope\n"
        "class Base:\n"
        "    def handle(self, request: ModelRequest) -> ModelResult: ...\n",
        encoding="utf-8",
    )
    (node / "handler.py").write_text(
        "from pkg.nodes.node_x.base import Base\n"
        "class HandlerRuntime(Base):\n"
        + ("    def handle(self, request): ...\n" if direct_handle else "    pass\n"),
        encoding="utf-8",
    )
    contract = node / "contract.yaml"
    contract.write_text(
        "handler:\n  module: pkg.nodes.node_x.handler\n  class: HandlerRuntime\n",
        encoding="utf-8",
    )

    finding = bindings.classify_node(contract)

    assert finding.category == ("canonical" if direct_handle else "envelope_in_core")
    assert finding.is_canonical is direct_handle


@pytest.mark.unit
@pytest.mark.parametrize(
    "source",
    ["class A(A): ...", "class A(B): ...\nclass B(A): ..."],
)
def test_handle_mro_cycle_terminates(tmp_path: Path, source: str) -> None:
    tree = ast.parse(source)
    cls = tree.body[0]
    assert isinstance(cls, ast.ClassDef)
    assert bindings._handle_via_mro(cls, [(tmp_path / "cycle.py", tree)]) == (
        None,
        None,
        None,
    )


@pytest.mark.unit
def test_handle_mro_depth_and_breadth_first_order(tmp_path: Path) -> None:
    tree = ast.parse(
        "class Child(Left, module.Right): ...\n"
        "class Left(Root): ...\n"
        "class Right:\n"
        "    def handle(self, request): ...\n"
        "class Root:\n"
        "    def handle(self, request): ...\n"
    )
    child = tree.body[0]
    left = tree.body[1]
    assert isinstance(child, ast.ClassDef)
    assert isinstance(left, ast.ClassDef)
    parsed = [(tmp_path / "hierarchy.py", tree)]
    assert bindings._base_class_names(child) == ["Left", "Right"]
    assert bindings._handle_via_mro(child, parsed, max_depth=0) == (None, None, None)
    fn, defining_class, path = bindings._handle_via_mro(child, parsed, max_depth=1)
    assert fn is not None
    assert defining_class is not None and defining_class.name == "Right"
    assert path == parsed[0][0]
    assert bindings._handle_via_mro(left, parsed, max_depth=1)[1] is tree.body[3]


@pytest.mark.unit
def test_new_node_without_handler_stays_no_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fscope.SCOPE, "src_root", tmp_path)
    node = tmp_path / "pkg/nodes/node_new"
    node.mkdir(parents=True)
    (node / "__init__.py").write_text("", encoding="utf-8")
    contract = node / "contract.yaml"
    contract.write_text("name: node_new\n", encoding="utf-8")

    finding = bindings.classify_node(contract)

    assert finding.category == "no_binding"
    assert not finding.is_canonical


def test_verify_flip_receipt_missing_file_fails_closed() -> None:
    ok, reason = receipts.verify_flip_receipt("n.no_receipt_here", handler_module=None)
    assert ok is False
    assert "adequacy receipt" in reason


def test_absent_baseline_grandfathers_nothing(tmp_path) -> None:
    """OMN-20559: no baseline file is a plain check, never a crash or a pass."""
    assert fscope.load_baseline(tmp_path / "absent_baseline.py") == []


def test_core_carries_no_handler_shape_baseline() -> None:
    """omnibase_core's baseline emptied; the gate is a plain check here."""
    assert not fscope.SCOPE.baseline_path.exists()


def test_resolve_scope_default_package_reproduces_current_constants() -> None:
    src_root, nodes_glob, baseline, receipts_dir = fscope._resolve_scope(
        "omnibase_core", None, None, None, None
    )
    assert src_root == fscope.SCOPE.src_root
    assert (
        nodes_glob
        == "omnibase_core/**/nodes/**/contract.yaml"
        == fscope.SCOPE.nodes_glob
    )
    assert baseline == fscope.SCOPE.baseline_path
    assert receipts_dir == fscope.SCOPE.receipts_dir


def test_resolve_scope_foreign_package_scopes_independently(tmp_path) -> None:
    foreign_src = tmp_path / "omnimarket" / "src"
    src_root, nodes_glob, baseline, receipts_dir = fscope._resolve_scope(
        "omnimarket", foreign_src, None, None, None
    )
    assert src_root == foreign_src
    assert nodes_glob == "omnimarket/**/nodes/**/contract.yaml"
    # Never falls back to omnibase_core's own committed baseline/receipts —
    # a forgotten --baseline on a foreign package must not silently clobber it.
    assert baseline.name == "flip_shape_baseline_omnimarket.py"
    assert baseline != fscope.SCOPE.baseline_path
    assert receipts_dir.name == "adequacy_receipts_omnimarket"
    assert receipts_dir != fscope.SCOPE.receipts_dir


def test_resolve_scope_explicit_overrides_win(tmp_path) -> None:
    explicit_baseline = tmp_path / "custom_baseline.py"
    explicit_receipts = tmp_path / "custom_receipts"
    src_root, nodes_glob, baseline, receipts_dir = fscope._resolve_scope(
        "omnimarket",
        tmp_path,
        "custom/**/glob.yaml",
        explicit_baseline,
        explicit_receipts,
    )
    assert src_root == tmp_path
    assert nodes_glob == "custom/**/glob.yaml"
    assert baseline == explicit_baseline
    assert receipts_dir == explicit_receipts


def _write_receipt(dir_path, name: str, **fields) -> None:
    import json

    (dir_path / f"{name}.json").write_text(json.dumps(fields), encoding="utf-8")


def test_forged_meets_target_is_recomputed_and_rejected(tmp_path, monkeypatch) -> None:
    # A forged receipt: below target but self-asserts meets_target=True, no waiver.
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", tmp_path)
    _write_receipt(
        tmp_path,
        "n.forged",
        node_id="n.forged",
        branch_coverage_pct=10.0,
        coverage_target=80.0,
        meets_target=True,  # LIE — gate must recompute 10 < 80
        handler_module="m",
        handler_module_sha256="sha256:whatever",
        selected_input_hashes=["h1"],
    )
    ok, reason, _ = artifacts.verify_adequacy_receipt("n.forged", handler_module=None)
    assert ok is False
    assert "below target" in reason


def test_recompute_accepts_real_pass_despite_false_flag(tmp_path, monkeypatch) -> None:
    # meets_target=False but numbers say pass (90>=80) — recompute wins.
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", tmp_path)
    monkeypatch.setattr(
        artifacts, "_resolve_module_file", lambda module: tmp_path / "m.py"
    )
    monkeypatch.setattr(artifacts, "_sha256_file", lambda path: "sha256:MATCH")
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")
    _write_receipt(
        tmp_path,
        "n.real",
        node_id="n.real",
        branch_coverage_pct=90.0,
        coverage_target=80.0,
        meets_target=False,  # gate ignores this; recomputes pass
        handler_module="m",
        handler_module_sha256="sha256:MATCH",
        selected_input_hashes=["h1"],
    )
    ok, reason, selected = artifacts.verify_adequacy_receipt(
        "n.real", handler_module=None
    )
    assert ok is True
    assert reason == "recomputed-meets-target"
    assert selected == ["h1"]


def test_stale_receipt_sha_mismatch_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", tmp_path)
    monkeypatch.setattr(
        artifacts, "_resolve_module_file", lambda module: tmp_path / "m.py"
    )
    monkeypatch.setattr(artifacts, "_sha256_file", lambda path: "sha256:LIVE_DIFFERENT")
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")
    _write_receipt(
        tmp_path,
        "n.stale",
        node_id="n.stale",
        branch_coverage_pct=90.0,
        coverage_target=80.0,
        meets_target=True,
        handler_module="m",
        handler_module_sha256="sha256:RECORDED_OLD",
        selected_input_hashes=["h1"],
    )
    ok, reason, _ = artifacts.verify_adequacy_receipt("n.stale", handler_module=None)
    assert ok is False
    assert "stale receipt" in reason


def test_flip_requires_green_equivalence_replay(tmp_path, monkeypatch) -> None:
    # Adequacy passes but there is no equivalence artifact -> flip fails.
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", tmp_path)
    monkeypatch.setattr(
        receipts,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "ok", ["h1"]),
    )
    ok, reason = receipts.verify_flip_receipt("n.noequiv", handler_module=None)
    assert ok is False
    assert "equivalence" in reason


def test_flip_pair_incompatible_when_input_sets_differ(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        receipts,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "ok", ["h1"]),
    )
    monkeypatch.setattr(
        receipts, "verify_equivalence_replay", lambda node_id: (True, "ok", ["h2"])
    )
    ok, reason = receipts.verify_flip_receipt("n.mismatch", handler_module=None)
    assert ok is False
    assert "PAIR_INCOMPATIBLE" in reason


def test_flip_passes_with_bound_adequacy_and_equivalence(monkeypatch) -> None:
    monkeypatch.setattr(
        receipts,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1", "h2"]),
    )
    monkeypatch.setattr(
        receipts,
        "verify_equivalence_replay",
        lambda node_id: (True, "equiv", ["h2", "h1"]),
    )
    ok, reason = receipts.verify_flip_receipt("n.good", handler_module=None)
    assert ok is True
    assert "cov" in reason and "equiv" in reason


def test_parse_non_canonical_extracts_tuple() -> None:
    source = (
        '"""doc"""\n'
        "NON_CANONICAL: tuple[str, ...] = (\n"
        '    "z.node",\n'
        '    "a.node",\n'
        ")\n"
    )
    assert fscope._parse_non_canonical(source) == ["z.node", "a.node"]
    assert fscope._parse_non_canonical("NON_CANONICAL: tuple[str, ...] = ()\n") == []


_LEGACY_HANDLER = """
class HandlerX:
    def handle(self, envelope):  # non-canonical shape (envelope in core)
        return self._compute(envelope.payload)

    def _compute(self, data):
        total = 0
        for row in data:
            total += row * 2
        return total
"""


_CANONICAL_HANDLER_SAME_LOGIC = """
class HandlerX:
    def handle(self, request: ModelReq) -> ModelResp:  # def-B shape
        return self._compute(request.rows)

    def _compute(self, data):
        total = 0
        for row in data:
            total += row * 2
        return total
"""


_CANONICAL_HANDLER_CHANGED_LOGIC = """
class HandlerX:
    def handle(self, request: ModelReq) -> ModelResp:
        return self._compute(request.rows)

    def _compute(self, data):
        return sum(r * 3 for r in data)  # LOGIC CHANGED
"""


def _write_handflip(dir_path, node_id: str, **overrides) -> None:
    import json

    body = {
        "receipt_schema": "handflip_proof.v1",
        "node_id": node_id,
        "canonical_handler_module": "pkg.handler",
        "legacy_handler_module": "pkg.handler",
        "base_ref": "origin/dev",
        "preserved_symbols": ["_compute"],
        "parity": {
            "test_ids": ["tests/test_parity.py::test_x"],
            "status": "pass",
            "selected_input_hashes": ["h1"],
        },
    }
    body.update(overrides)
    (dir_path / f"{node_id}.handflip.json").write_text(
        json.dumps(body), encoding="utf-8"
    )


def _parity_executor(*, executed: bool = True, green: bool = True):
    """An INJECTED parity verdict.

    OMN-15340 made the executed verdict the evidence, so a hand-flip unit test must
    say which verdict it is assuming instead of leaning on the receipt's ``status``
    string. Without an injected executor the real one runs pytest against the working
    tree — correct in production, meaningless against these synthetic receipts.
    """

    def _executor(node_id: str, test_ids: tuple[str, ...]):
        return ModelParityVerdict(
            executed=executed, green=green, detail=f"stubbed verdict for {test_ids}"
        )

    return _executor


def _handflip_env(tmp_path, monkeypatch, head_src: str, base_src: str) -> None:
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", tmp_path)
    head_file = tmp_path / "head_handler.py"
    head_file.write_text(head_src, encoding="utf-8")
    monkeypatch.setattr(receipts, "_resolve_module_file", lambda module: head_file)
    monkeypatch.setattr(
        receipts, "_module_repo_rel", lambda module: (tmp_path, "src/legacy.py")
    )
    monkeypatch.setattr(receipts, "_git_ref_exists", lambda repo_root, ref: True)
    monkeypatch.setattr(
        receipts, "_git_show", lambda repo_root, ref, rel_path: base_src
    )


def test_handflip_proof_verbatim_preserved_passes(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand")
    ok, reason, selected = receipts.verify_handflip_proof(
        "n.hand", handler_module="pkg.handler", parity_executor=_parity_executor()
    )
    assert ok is True, reason
    assert "verbatim" in reason
    assert selected == ["h1"]


def test_handflip_proof_diverged_logic_fails(tmp_path, monkeypatch) -> None:
    # The preserved symbol's body differs between BASE and HEAD -> not verbatim.
    _handflip_env(
        tmp_path, monkeypatch, _CANONICAL_HANDLER_CHANGED_LOGIC, _LEGACY_HANDLER
    )
    _write_handflip(tmp_path, "n.hand")
    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand", handler_module="pkg.handler", parity_executor=_parity_executor()
    )
    assert ok is False
    assert "verbatim-preservation FAILED" in reason


def test_handflip_proof_missing_symbol_in_head_fails(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand", preserved_symbols=["_does_not_exist"])
    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand", handler_module="pkg.handler", parity_executor=_parity_executor()
    )
    assert ok is False
    assert "not all found in HEAD" in reason


def test_handflip_proof_parity_not_pass_fails(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(
        tmp_path,
        "n.hand",
        parity={"test_ids": ["t::x"], "status": "fail", "selected_input_hashes": []},
    )
    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand", handler_module="pkg.handler", parity_executor=_parity_executor()
    )
    assert ok is False
    assert "parity" in reason


def test_handflip_proof_missing_artifact_fails() -> None:
    ok, reason, _ = receipts.verify_handflip_proof(
        "n.absent", handler_module="pkg.handler", parity_executor=_parity_executor()
    )
    assert ok is False
    assert "no hand-flip proof artifact" in reason


def test_handflip_proof_rejects_unexecuted_parity_claim(tmp_path, monkeypatch) -> None:
    """OMN-15340: a recorded ``status: pass`` earns nothing on its own.

    The receipt is otherwise perfect — verbatim-preserved symbols, a well-formed
    parity block, ``status: pass``. Before OMN-15340 that was accepted. Now an
    executor that could not run the declared ids rejects it.
    """
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand")

    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand",
        handler_module="pkg.handler",
        parity_executor=_parity_executor(executed=False, green=False),
    )

    assert ok is False
    assert "UNEXECUTED" in reason
    assert "not evidence" in reason


def test_handflip_proof_rejects_executed_but_red_parity(tmp_path, monkeypatch) -> None:
    """status=pass over tests that are actually RED on HEAD -> rejected."""
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand")

    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand",
        handler_module="pkg.handler",
        parity_executor=_parity_executor(executed=True, green=False),
    )

    assert ok is False
    assert "NOT GREEN when executed" in reason


def test_handflip_proof_reason_names_the_executed_parity(tmp_path, monkeypatch) -> None:
    """The success reason must record that parity was EXECUTED, not just declared."""
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand")

    ok, reason, _ = receipts.verify_handflip_proof(
        "n.hand", handler_module="pkg.handler", parity_executor=_parity_executor()
    )

    assert ok is True, reason
    assert "parity-executed-green" in reason


def test_default_parity_executor_fails_closed_without_a_git_root(
    tmp_path, monkeypatch
) -> None:
    """No repo -> no execution -> no credit (never a silent skip)."""
    monkeypatch.setattr(fscope.SCOPE, "src_root", tmp_path / "src")
    monkeypatch.setattr(parity, "_git_repo_root", lambda path: None)
    monkeypatch.setattr(parity, "_PARITY_CACHE", {})

    verdict = parity.default_parity_executor("n.hand", ("tests/t.py::test_x",))

    assert verdict.executed is False
    assert verdict.green is False


def test_flip_accepts_handflip_path(tmp_path, monkeypatch) -> None:
    # receipts.verify_flip_receipt takes the hand-flip branch when equivalence is absent but a
    # valid hand-flip proof exists, and binds input sets receipt<->parity.
    monkeypatch.setattr(
        receipts,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1"]),
    )
    monkeypatch.setattr(
        receipts, "verify_equivalence_replay", lambda node_id: (False, "absent", [])
    )
    monkeypatch.setattr(
        receipts,
        "verify_handflip_proof",
        lambda node_id, handler_module, **kwargs: (
            True,
            "handflip-verbatim-preserved",
            ["h1"],
        ),
    )
    ok, reason = receipts.verify_flip_receipt("n.hand", handler_module="pkg.handler")
    assert ok is True
    assert "handflip" in reason


def test_flip_handflip_pair_incompatible_when_input_sets_differ(monkeypatch) -> None:
    monkeypatch.setattr(
        receipts,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1"]),
    )
    monkeypatch.setattr(
        receipts, "verify_equivalence_replay", lambda node_id: (False, "absent", [])
    )
    monkeypatch.setattr(
        receipts,
        "verify_handflip_proof",
        lambda node_id, handler_module, **kwargs: (True, "handflip", ["hX"]),
    )
    ok, reason = receipts.verify_flip_receipt("n.hand", handler_module="pkg.handler")
    assert ok is False
    assert "PAIR_INCOMPATIBLE" in reason


def test_extract_symbol_sources_qualified_and_bare() -> None:
    src = "class A:\n    def m(self):\n        return 1\ndef top():\n    return 2\n"
    bare = artifacts._extract_symbol_sources(src, ["m", "top"])
    assert bare is not None and set(bare) == {"m", "top"}
    qual = artifacts._extract_symbol_sources(src, ["A.m"])
    assert qual is not None and set(qual) == {"A.m"}
    assert artifacts._extract_symbol_sources(src, ["nope"]) is None


def test_receipt_path_display_no_crash_outside_repo_root(tmp_path, monkeypatch) -> None:
    """Under fan-out, RECEIPTS_DIR is a SIBLING repo outside this classifier's
    REPO_ROOT. The old ``receipt_path.relative_to(REPO_ROOT)`` raised ValueError and
    crashed the gate. It must now degrade to a plain path in the message."""
    foreign = tmp_path / "omnimarket" / "scripts" / "ci" / "adequacy_receipts"
    foreign.mkdir(parents=True)
    monkeypatch.setattr(fscope.SCOPE, "receipts_dir", foreign)
    # No receipt on disk -> the missing-receipt message path (the one that crashed).
    ok, reason, _ = artifacts.verify_adequacy_receipt(
        "omnimarket.nodes.node_x", handler_module=None
    )
    assert ok is False
    assert "no adequacy receipt at" in reason
    assert "node_x" in reason  # rendered the path instead of raising
