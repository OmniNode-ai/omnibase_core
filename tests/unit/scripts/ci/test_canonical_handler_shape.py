# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the canonical handler-shape growth ratchet (OMN-14355).

Covers the classifier (definition B), the ratchet enforcement (new/growth
hard-fail, warn-only baseline), and — the load-bearing guard — that a baselined
node flipping to canonical shape WITHOUT an adequacy receipt hard-fails (a shape
flip is not proof of equivalence; the OMN-14208-at-scale trap).
"""

from __future__ import annotations

import ast
import subprocess
import sys

import pytest

import scripts.ci.canonical_handler_shape as mod
from scripts.ci.canonical_handler_shape import (
    ModelHandlerShapeFinding,
    _contract_bindings,
    _escalation_reason,
    _extract_symbol_sources,
    _handle_is_adaptable,
    _parse_non_canonical,
    _resolve_scope,
    _touched_node_ids,
    classify_all,
    current_non_canonical,
    evaluate,
    load_baseline,
    verify_adequacy_receipt,
    verify_flip_receipt,
    verify_handflip_proof,
    write_baseline,
)


def _handle_fn(src: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
    return fn


# --------------------------------------------------------------------------- #
# Classifier — signature adaptability (definition B)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("src", "adaptable"),
    [
        ("def handle(self, request: ModelFoo) -> ModelBar: ...", True),
        ("def handle(self, command: ModelStart) -> ModelDone: ...", True),
        ("def handle(self, payload): ...", True),
        ("def handle(self): ...", True),
        ("def handle(self, **kwargs): ...", True),
        ("async def handle(self, request: ModelReq) -> ModelResp: ...", True),
        ("def handle(self, input_data: dict[str, object]): ...", False),
        ("def handle(self, correlation_id, input_data): ...", False),
        ("def handle(self, envelope: Any) -> Any: ...", False),
        ("def handle(self, thing: list[str]): ...", False),
    ],
)
def test_handle_is_adaptable(src: str, adaptable: bool) -> None:
    ok, _reason = _handle_is_adaptable(_handle_fn(src))
    assert ok is adaptable


# --------------------------------------------------------------------------- #
# Classifier — contract binding schema variants
# --------------------------------------------------------------------------- #


def test_contract_bindings_explicit_module() -> None:
    data = {"handler": {"module": "pkg.nodes.node_x.handlers.h", "class": "HandlerX"}}
    assert _contract_bindings(data)[0] == ("pkg.nodes.node_x.handlers.h", "HandlerX")


def test_contract_bindings_default_handler() -> None:
    data = {"handler_routing": {"default_handler": "handler:NodeX"}}
    module, cls = _contract_bindings(data)[0]
    assert cls == "NodeX"
    assert module == ""  # no module in "handler:NodeX" — resolved from node package


def test_contract_bindings_default_handler_with_module() -> None:
    data = {"handler_routing": {"default_handler": "pkg.nodes.node_x.handler:NodeX"}}
    assert _contract_bindings(data)[0] == ("pkg.nodes.node_x.handler", "NodeX")


def test_contract_bindings_none_when_handler_id_only() -> None:
    # handler_id-only contracts fall back to the node package at classify time.
    assert _contract_bindings({"handler_id": "node.x", "input_model": "pkg.M"}) == []


# --------------------------------------------------------------------------- #
# Ratchet enforcement
# --------------------------------------------------------------------------- #


def _nc(node_id: str) -> ModelHandlerShapeFinding:
    return ModelHandlerShapeFinding(
        node_id=node_id,
        category="op_method",
        is_canonical=False,
        handler_module=node_id,
    )


def _canon(node_id: str) -> ModelHandlerShapeFinding:
    return ModelHandlerShapeFinding(
        node_id=node_id, category="canonical", is_canonical=True, handler_module=node_id
    )


def test_clean_state_passes() -> None:
    findings = [_nc("n.a"), _canon("n.b")]
    result = evaluate(findings, baseline=["n.a"])
    assert not result.failed
    assert result.warn_baselined == ("n.a",)


def test_new_non_canonical_node_hard_fails() -> None:
    findings = [_nc("n.a"), _nc("n.new"), _canon("n.b")]
    result = evaluate(findings, baseline=["n.a"])
    assert result.failed
    assert result.new_non_canonical == ("n.new",)


def test_unproven_flip_hard_fails() -> None:
    # A baselined node became canonical but has no adequacy receipt on disk —
    # a shape flip is not proof of equivalence. This must hard-fail.
    findings = [_canon("n.a")]
    result = evaluate(findings, baseline=["n.a"])
    assert result.failed
    assert result.unproven_flips == ("n.a",)
    assert result.proven_flips == ()


def test_proven_flip_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.ci.canonical_handler_shape as mod

    monkeypatch.setattr(
        mod,
        "verify_flip_receipt",
        lambda node_id, handler_module: (True, "meets_target"),
    )
    findings = [_canon("n.a")]
    result = evaluate(findings, baseline=["n.a"])
    assert not result.failed
    assert result.proven_flips == ("n.a",)


def test_deleted_baselined_node_is_ignored() -> None:
    # A baselined node no longer present (deleted) is neither a flip nor a failure.
    result = evaluate([_canon("n.b")], baseline=["n.gone"])
    assert not result.failed
    assert result.unproven_flips == ()


# --------------------------------------------------------------------------- #
# Adequacy-gated flip
# --------------------------------------------------------------------------- #


def test_verify_flip_receipt_missing_file_fails_closed() -> None:
    ok, reason = verify_flip_receipt("n.no_receipt_here", handler_module=None)
    assert ok is False
    assert "adequacy receipt" in reason


# --------------------------------------------------------------------------- #
# Baseline round-trip
# --------------------------------------------------------------------------- #


def test_baseline_roundtrip(tmp_path) -> None:
    path = tmp_path / "baseline.py"
    write_baseline(["z.node", "a.node"], path)
    assert load_baseline(path) == ["a.node", "z.node"]  # sorted, deterministic


# --------------------------------------------------------------------------- #
# Live regression guard (like the import-ratchet live test)
# --------------------------------------------------------------------------- #


def test_live_classification_matches_committed_baseline() -> None:
    """The live ombase_core node graph introduces no NEW non-canonical node and
    no unproven flip against the committed baseline."""
    findings = classify_all()
    baseline = load_baseline()
    result = evaluate(findings, baseline)
    assert not result.failed, (
        f"new={result.new_non_canonical} unproven_flips={result.unproven_flips}"
    )


def test_live_known_shapes() -> None:
    """Anchor the classifier to two real, hand-verified core nodes."""
    by_id = {f.node_id: f for f in classify_all()}
    verify = by_id["omnibase_core.nodes.node_contract_verify_replay_compute"]
    assert verify.is_canonical and verify.category == "canonical"
    backend = by_id["omnibase_core.nodes.node_backend_secret_discipline_compute"]
    assert backend.is_canonical and backend.category == "canonical"


def test_live_shape_debt_is_fully_drained() -> None:
    findings = classify_all()
    assert any(f.is_canonical for f in findings)
    assert current_non_canonical(findings) == []


# --------------------------------------------------------------------------- #
# Change-aware scoping
# --------------------------------------------------------------------------- #


def test_touched_node_ids_maps_paths_to_nodes() -> None:
    changed = [
        "src/omnibase_core/nodes/node_alpha/handler.py",
        "src/omnibase_core/nodes/node_beta/contract.yaml",
        "README.md",
        "src/omnibase_core/runtime/runtime_local.py",  # not under /nodes/
    ]
    assert _touched_node_ids(changed) == {
        "omnibase_core.nodes.node_alpha",
        "omnibase_core.nodes.node_beta",
    }


def test_escalation_on_gate_and_resolution_and_shared_modules() -> None:
    assert _escalation_reason(["scripts/ci/canonical_handler_shape.py"]) is not None
    assert (
        _escalation_reason(["scripts/ci/canonical_handler_shape_baseline.py"])
        is not None
    )
    assert (
        _escalation_reason(["src/omnibase_core/runtime/runtime_local_adapter.py"])
        is not None
    )
    assert (
        _escalation_reason(["src/omnibase_core/mixins/mixin_envelope_extraction.py"])
        is not None
    )


def test_no_escalation_for_plain_node_change() -> None:
    assert _escalation_reason(["src/omnibase_core/nodes/node_x/handler.py"]) is None
    assert _escalation_reason(["docs/foo.md"]) is None


# --------------------------------------------------------------------------- #
# Package scoping (OMN-14368 mechanical-wave fan-out)
# --------------------------------------------------------------------------- #
#
# _resolve_scope is pure (no global mutation) so these tests never touch
# mod.SRC_ROOT/BASELINE_PATH/RECEIPTS_DIR/PACKAGE — the live regression guards
# above (test_live_classification_matches_committed_baseline et al.) keep
# reading the untouched omnibase_core defaults for the whole test session.


def test_resolve_scope_default_package_reproduces_current_constants() -> None:
    src_root, nodes_glob, baseline, receipts_dir = _resolve_scope(
        "omnibase_core", None, None, None, None
    )
    assert src_root == mod.SRC_ROOT
    assert nodes_glob == "omnibase_core/**/nodes/**/contract.yaml" == mod.NODES_GLOB
    assert baseline == mod.BASELINE_PATH
    assert receipts_dir == mod.RECEIPTS_DIR


def test_resolve_scope_foreign_package_scopes_independently(tmp_path) -> None:
    foreign_src = tmp_path / "omnimarket" / "src"
    src_root, nodes_glob, baseline, receipts_dir = _resolve_scope(
        "omnimarket", foreign_src, None, None, None
    )
    assert src_root == foreign_src
    assert nodes_glob == "omnimarket/**/nodes/**/contract.yaml"
    # Never falls back to omnibase_core's own committed baseline/receipts —
    # a forgotten --baseline on a foreign package must not silently clobber it.
    assert baseline.name == "canonical_handler_shape_baseline_omnimarket.py"
    assert baseline != mod.BASELINE_PATH
    assert receipts_dir.name == "adequacy_receipts_omnimarket"
    assert receipts_dir != mod.RECEIPTS_DIR


def test_resolve_scope_explicit_overrides_win(tmp_path) -> None:
    explicit_baseline = tmp_path / "custom_baseline.py"
    explicit_receipts = tmp_path / "custom_receipts"
    src_root, nodes_glob, baseline, receipts_dir = _resolve_scope(
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


def test_cli_full_scan_default_package_unchanged() -> None:
    """``--full`` with no --package still checks omnibase_core's own committed
    baseline end to end. Runs in a subprocess (not in-process main()) so the
    scope mutation main() applies to module globals can never leak into other
    tests in this session."""
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.ci.canonical_handler_shape", "--full"],
        cwd=mod.REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ratchet OK" in proc.stdout


# --------------------------------------------------------------------------- #
# Recompute-not-trust: the receipt's self-asserted booleans are ignored
# --------------------------------------------------------------------------- #


def _write_receipt(dir_path, name: str, **fields) -> None:
    import json

    (dir_path / f"{name}.json").write_text(json.dumps(fields), encoding="utf-8")


def test_forged_meets_target_is_recomputed_and_rejected(tmp_path, monkeypatch) -> None:
    # A forged receipt: below target but self-asserts meets_target=True, no waiver.
    monkeypatch.setattr(mod, "RECEIPTS_DIR", tmp_path)
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
    ok, reason, _ = verify_adequacy_receipt("n.forged", handler_module=None)
    assert ok is False
    assert "below target" in reason


def test_recompute_accepts_real_pass_despite_false_flag(tmp_path, monkeypatch) -> None:
    # meets_target=False but numbers say pass (90>=80) — recompute wins.
    monkeypatch.setattr(mod, "RECEIPTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "_resolve_module_file", lambda module: tmp_path / "m.py")
    monkeypatch.setattr(mod, "_sha256_file", lambda path: "sha256:MATCH")
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
    ok, reason, selected = verify_adequacy_receipt("n.real", handler_module=None)
    assert ok is True
    assert reason == "recomputed-meets-target"
    assert selected == ["h1"]


def test_stale_receipt_sha_mismatch_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "RECEIPTS_DIR", tmp_path)
    monkeypatch.setattr(mod, "_resolve_module_file", lambda module: tmp_path / "m.py")
    monkeypatch.setattr(mod, "_sha256_file", lambda path: "sha256:LIVE_DIFFERENT")
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
    ok, reason, _ = verify_adequacy_receipt("n.stale", handler_module=None)
    assert ok is False
    assert "stale receipt" in reason


def test_flip_requires_green_equivalence_replay(tmp_path, monkeypatch) -> None:
    # Adequacy passes but there is no equivalence artifact -> flip fails.
    monkeypatch.setattr(mod, "RECEIPTS_DIR", tmp_path)
    monkeypatch.setattr(
        mod,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "ok", ["h1"]),
    )
    ok, reason = verify_flip_receipt("n.noequiv", handler_module=None)
    assert ok is False
    assert "equivalence" in reason


def test_flip_pair_incompatible_when_input_sets_differ(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "ok", ["h1"]),
    )
    monkeypatch.setattr(
        mod, "verify_equivalence_replay", lambda node_id: (True, "ok", ["h2"])
    )
    ok, reason = verify_flip_receipt("n.mismatch", handler_module=None)
    assert ok is False
    assert "PAIR_INCOMPATIBLE" in reason


def test_flip_passes_with_bound_adequacy_and_equivalence(monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1", "h2"]),
    )
    monkeypatch.setattr(
        mod, "verify_equivalence_replay", lambda node_id: (True, "equiv", ["h2", "h1"])
    )
    ok, reason = verify_flip_receipt("n.good", handler_module=None)
    assert ok is True
    assert "cov" in reason and "equiv" in reason


# --------------------------------------------------------------------------- #
# OMN-14781: git-BASE baseline comparison closes the in-PR-edit hole
# --------------------------------------------------------------------------- #


def test_in_pr_baseline_removal_negative_fixture() -> None:
    """THE regression fixture: a node flipped to canonical shape AND removed from
    NON_CANONICAL in the same commit, with NO flip proof.

    This is the exact shape of omnimarket#1815 (node_delegation_orchestrator). The
    OLD gate (no git-BASE comparison) PASSES it — the false-green hole. The NEW gate
    (git-BASE baseline supplied) FAILS it as an unproven flip.
    """
    findings = [_canon("n.flipped")]

    # OLD gate behavior == base_baseline unavailable (None): compares live scan only
    # against the post-edit committed baseline (which no longer lists the node).
    old = evaluate(findings, baseline=[], base_baseline=None)
    assert not old.failed, "OLD gate must PASS the hole (documents the false-green)"
    assert old.unproven_flips == ()

    # NEW gate: the node was present at the git BASE but removed in-PR -> claimed
    # flip -> proof required -> none on disk -> hard-fail.
    new = evaluate(findings, baseline=[], base_baseline=["n.flipped"])
    assert new.failed, "NEW gate must FAIL the previously-evaded flip"
    assert new.unproven_flips == ("n.flipped",)
    assert new.new_non_canonical == ()  # it's a removal-flip, not a NEW non-canonical


def test_in_pr_removal_with_valid_proof_passes(monkeypatch) -> None:
    monkeypatch.setattr(
        mod, "verify_flip_receipt", lambda node_id, handler_module: (True, "proven")
    )
    result = evaluate([_canon("n.flipped")], baseline=[], base_baseline=["n.flipped"])
    assert not result.failed
    assert result.proven_flips == ("n.flipped",)
    assert result.unproven_flips == ()


def test_in_pr_removal_still_noncanonical_is_new_nc_only() -> None:
    # Removed from baseline but the code did NOT flip -> a NEW non-canonical node
    # (new_nc), reported once, not also as an unproven flip.
    result = evaluate([_nc("n.x")], baseline=[], base_baseline=["n.x"])
    assert result.failed
    assert result.new_non_canonical == ("n.x",)
    assert result.unproven_flips == ()


def test_in_pr_removal_of_deleted_node_is_ok() -> None:
    # Removed from the baseline AND the node no longer exists (not in findings):
    # the removal is self-justifying — deletion cannot be non-canonical.
    result = evaluate([_canon("n.other")], baseline=[], base_baseline=["n.gone"])
    assert not result.failed
    assert result.unproven_flips == ()


def test_baseline_growth_hard_fails() -> None:
    # The baseline is monotonically non-increasing: hand-ADDING a node to silence a
    # new non-canonical node (base has fewer than working) is illegal growth.
    result = evaluate(
        [_nc("n.a"), _nc("n.added")],
        baseline=["n.a", "n.added"],
        base_baseline=["n.a"],
    )
    assert result.failed
    assert result.baseline_growth == ("n.added",)


def test_base_baseline_none_reproduces_old_behavior() -> None:
    # With base_baseline=None the removal/growth checks are inert -> identical to the
    # pre-OMN-14781 gate (no regression for the diff-unavailable path).
    findings = [_nc("n.a"), _canon("n.b")]
    result = evaluate(findings, baseline=["n.a"], base_baseline=None)
    assert not result.failed
    assert result.baseline_growth == ()


def test_parse_non_canonical_extracts_tuple() -> None:
    source = (
        '"""doc"""\n'
        "NON_CANONICAL: tuple[str, ...] = (\n"
        '    "z.node",\n'
        '    "a.node",\n'
        ")\n"
    )
    assert _parse_non_canonical(source) == ["z.node", "a.node"]
    assert _parse_non_canonical("NON_CANONICAL: tuple[str, ...] = ()\n") == []


# --------------------------------------------------------------------------- #
# OMN-14781: sanctioned HAND-FLIP proof path (verbatim-preservation, no fabricated
# equivalence-replay)
# --------------------------------------------------------------------------- #


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


def _handflip_env(tmp_path, monkeypatch, head_src: str, base_src: str) -> None:
    monkeypatch.setattr(mod, "RECEIPTS_DIR", tmp_path)
    head_file = tmp_path / "head_handler.py"
    head_file.write_text(head_src, encoding="utf-8")
    monkeypatch.setattr(mod, "_resolve_module_file", lambda module: head_file)
    monkeypatch.setattr(
        mod, "_module_repo_rel", lambda module: (tmp_path, "src/legacy.py")
    )
    monkeypatch.setattr(mod, "_git_ref_exists", lambda repo_root, ref: True)
    monkeypatch.setattr(mod, "_git_show", lambda repo_root, ref, rel_path: base_src)


def test_handflip_proof_verbatim_preserved_passes(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand")
    ok, reason, selected = verify_handflip_proof("n.hand", handler_module="pkg.handler")
    assert ok is True, reason
    assert "verbatim" in reason
    assert selected == ["h1"]


def test_handflip_proof_diverged_logic_fails(tmp_path, monkeypatch) -> None:
    # The preserved symbol's body differs between BASE and HEAD -> not verbatim.
    _handflip_env(
        tmp_path, monkeypatch, _CANONICAL_HANDLER_CHANGED_LOGIC, _LEGACY_HANDLER
    )
    _write_handflip(tmp_path, "n.hand")
    ok, reason, _ = verify_handflip_proof("n.hand", handler_module="pkg.handler")
    assert ok is False
    assert "verbatim-preservation FAILED" in reason


def test_handflip_proof_missing_symbol_in_head_fails(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(tmp_path, "n.hand", preserved_symbols=["_does_not_exist"])
    ok, reason, _ = verify_handflip_proof("n.hand", handler_module="pkg.handler")
    assert ok is False
    assert "not all found in HEAD" in reason


def test_handflip_proof_parity_not_pass_fails(tmp_path, monkeypatch) -> None:
    _handflip_env(tmp_path, monkeypatch, _CANONICAL_HANDLER_SAME_LOGIC, _LEGACY_HANDLER)
    _write_handflip(
        tmp_path,
        "n.hand",
        parity={"test_ids": ["t::x"], "status": "fail", "selected_input_hashes": []},
    )
    ok, reason, _ = verify_handflip_proof("n.hand", handler_module="pkg.handler")
    assert ok is False
    assert "parity" in reason


def test_handflip_proof_missing_artifact_fails() -> None:
    ok, reason, _ = verify_handflip_proof("n.absent", handler_module="pkg.handler")
    assert ok is False
    assert "no hand-flip proof artifact" in reason


def test_flip_accepts_handflip_path(tmp_path, monkeypatch) -> None:
    # verify_flip_receipt takes the hand-flip branch when equivalence is absent but a
    # valid hand-flip proof exists, and binds input sets receipt<->parity.
    monkeypatch.setattr(
        mod,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1"]),
    )
    monkeypatch.setattr(
        mod, "verify_equivalence_replay", lambda node_id: (False, "absent", [])
    )
    monkeypatch.setattr(
        mod,
        "verify_handflip_proof",
        lambda node_id, handler_module: (True, "handflip-verbatim-preserved", ["h1"]),
    )
    ok, reason = verify_flip_receipt("n.hand", handler_module="pkg.handler")
    assert ok is True
    assert "handflip" in reason


def test_flip_handflip_pair_incompatible_when_input_sets_differ(monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "verify_adequacy_receipt",
        lambda node_id, handler_module: (True, "cov", ["h1"]),
    )
    monkeypatch.setattr(
        mod, "verify_equivalence_replay", lambda node_id: (False, "absent", [])
    )
    monkeypatch.setattr(
        mod,
        "verify_handflip_proof",
        lambda node_id, handler_module: (True, "handflip", ["hX"]),
    )
    ok, reason = verify_flip_receipt("n.hand", handler_module="pkg.handler")
    assert ok is False
    assert "PAIR_INCOMPATIBLE" in reason


def test_extract_symbol_sources_qualified_and_bare() -> None:
    src = "class A:\n    def m(self):\n        return 1\ndef top():\n    return 2\n"
    bare = _extract_symbol_sources(src, ["m", "top"])
    assert bare is not None and set(bare) == {"m", "top"}
    qual = _extract_symbol_sources(src, ["A.m"])
    assert qual is not None and set(qual) == {"A.m"}
    assert _extract_symbol_sources(src, ["nope"]) is None


# --------------------------------------------------------------------------- #
# OMN-14781: core receipt-path classifier crash under fan-out
# --------------------------------------------------------------------------- #


def test_receipt_path_display_no_crash_outside_repo_root(tmp_path, monkeypatch) -> None:
    """Under fan-out, RECEIPTS_DIR is a SIBLING repo outside this classifier's
    REPO_ROOT. The old ``receipt_path.relative_to(REPO_ROOT)`` raised ValueError and
    crashed the gate. It must now degrade to a plain path in the message."""
    foreign = tmp_path / "omnimarket" / "scripts" / "ci" / "adequacy_receipts"
    foreign.mkdir(parents=True)
    monkeypatch.setattr(mod, "RECEIPTS_DIR", foreign)
    # No receipt on disk -> the missing-receipt message path (the one that crashed).
    ok, reason, _ = verify_adequacy_receipt(
        "omnimarket.nodes.node_x", handler_module=None
    )
    assert ok is False
    assert "no adequacy receipt at" in reason
    assert "node_x" in reason  # rendered the path instead of raising
