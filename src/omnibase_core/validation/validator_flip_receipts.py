# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-derive hand-flip proof and bind each flip to its adequacy evidence."""

from __future__ import annotations

from omnibase_core.validation.validator_flip_artifacts import (
    EXPECTED_HANDFLIP_SCHEMA,
    HANDFLIP_SUFFIX,
    _extract_symbol_sources,
    _load_json,
    _module_repo_rel,
    _resolve_module_file,
    verify_adequacy_receipt,
    verify_equivalence_replay,
)
from omnibase_core.validation.validator_flip_git import _git_ref_exists, _git_show
from omnibase_core.validation.validator_flip_no_legacy import verify_no_legacy_flip
from omnibase_core.validation.validator_flip_parity import (
    ParityExecutor,
    default_parity_executor,
)
from omnibase_core.validation.validator_flip_scope import SCOPE


def verify_handflip_proof(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str, list[str]]:
    """Sanctioned proof for a HAND-authored def-B flip (no fabricated replay).

    Re-derives verbatim-preservation from git itself — the gate reads the named
    business-logic symbols from the git-BASE legacy module AND the HEAD canonical
    module and requires them byte-identical (post AST-normalization). This cannot
    be faked by writing a JSON file: the symbols must genuinely be unchanged across
    the flip.

    Parity tests attest the behavior the verbatim check cannot cover, and since
    OMN-15340 they are EXECUTED rather than credited from ``parity.status``: the
    declared ids must run GREEN on HEAD through ``parity_executor`` (default:
    ``default_parity_executor``, which really runs pytest). The complementary half —
    that those same ids are RED on the receipt's own ``base_ref``, i.e. that they
    discriminate the flip at all — is assertion 7 of ``verify_flip_bundle``. The
    input-set binding is enforced by ``verify_flip_receipt``.

    Returns ``(ok, reason, selected_input_hashes)``.
    """
    art_path = SCOPE.receipts_dir / f"{node_id}{HANDFLIP_SUFFIX}"
    if not art_path.exists():
        return False, "no hand-flip proof artifact", []
    raw = _load_json(art_path)
    if raw is None:
        return False, "hand-flip artifact unparseable", []
    if raw.get("node_id") != node_id:
        return False, "hand-flip artifact node_id mismatch", []
    schema = raw.get("receipt_schema")
    if schema != EXPECTED_HANDFLIP_SCHEMA:
        return False, f"unexpected hand-flip receipt_schema {schema!r}", []

    symbols_raw = raw.get("preserved_symbols")
    symbols = [str(s) for s in symbols_raw] if isinstance(symbols_raw, list) else []
    if not symbols:
        return False, "hand-flip proof declares no preserved_symbols", []

    canonical_module = raw.get("canonical_handler_module") or handler_module
    legacy_module = raw.get("legacy_handler_module")
    base_ref = raw.get("base_ref")
    if not isinstance(canonical_module, str) or not canonical_module:
        return False, "hand-flip proof missing canonical_handler_module", []
    if not isinstance(legacy_module, str) or not legacy_module:
        return False, "hand-flip proof missing legacy_handler_module", []
    if not isinstance(base_ref, str) or not base_ref:
        return False, "hand-flip proof missing base_ref", []

    # HEAD side: live working-tree canonical module.
    head_file = _resolve_module_file(canonical_module)
    if head_file is None:
        return False, f"canonical_handler_module {canonical_module} not resolvable", []
    head_bodies = _extract_symbol_sources(
        head_file.read_text(encoding="utf-8"), symbols
    )
    if head_bodies is None:
        return False, "preserved_symbols not all found in HEAD module", []

    # BASE side: legacy module as of base_ref, read from git (never fabricated).
    rel = _module_repo_rel(legacy_module)
    if rel is None:
        return False, f"legacy_handler_module {legacy_module} path unresolvable", []
    repo_root, rel_path = rel
    if not _git_ref_exists(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} unresolvable for verbatim check", []
    base_source = _git_show(repo_root, base_ref, rel_path)
    if base_source is None:
        return False, f"legacy module absent at {base_ref}:{rel_path}", []
    base_bodies = _extract_symbol_sources(base_source, symbols)
    if base_bodies is None:
        return False, "preserved_symbols not all found in git-BASE legacy module", []

    diverged = sorted(s for s in symbols if head_bodies[s] != base_bodies[s])
    if diverged:
        return (
            False,
            f"verbatim-preservation FAILED — logic changed for {diverged}",
            [],
        )

    parity = raw.get("parity")
    if not isinstance(parity, dict):
        return False, "hand-flip proof missing parity block", []
    if parity.get("status") != "pass":
        # A self-declared failure is a confession — trusted in the negative direction
        # only. A self-declared ``pass`` earns nothing; it must be executed below.
        return False, f"parity tests status={parity.get('status')!r}", []
    test_ids = parity.get("test_ids")
    if not isinstance(test_ids, list) or not test_ids:
        return False, "hand-flip parity block names no test_ids", []

    # OMN-15340: run them or reject them. The recorded ``status`` never survives as
    # evidence on its own.
    executor = (
        parity_executor if parity_executor is not None else default_parity_executor
    )
    verdict = executor(node_id, tuple(str(t) for t in test_ids))
    if not verdict.executed:
        return (
            False,
            f"parity claim UNEXECUTED — a recorded status string is not evidence "
            f"({verdict.detail})",
            [],
        )
    if not verdict.green:
        return False, f"parity tests NOT GREEN when executed: {verdict.detail}", []

    hashes = parity.get("selected_input_hashes")
    selected = [str(h) for h in hashes] if isinstance(hashes, list) else []
    return (
        True,
        f"handflip-verbatim-preserved({len(symbols)} symbol(s))"
        f"+parity-executed-green({len(test_ids)} test id(s))",
        selected,
    )


def verify_flip_receipt(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason) for a non-canonical -> canonical baseline flip.

    Requires an adequacy receipt (re-derived verdict) AND one of two sanctioned
    behavior proofs, each bound to the SAME selected input set as the receipt:
      * RSD regen path: a GREEN regen-vs-legacy equivalence-replay artifact; OR
      * HAND-flip path (OMN-14781): a hand-flip proof whose verbatim-preservation
        the gate re-derives from git and whose declared parity tests it EXECUTES
        green on HEAD (OMN-15340 — the recorded status string is not evidence).
    Fail-closed: no adequacy, or neither proof, or a mismatched input set -> RED.

    An adequacy receipt carrying ``legacy_handler`` takes the NO-LEGACY path
    (OMN-20298, ``verify_no_legacy_flip``) and only that path.
    """
    raw = _load_json(SCOPE.receipts_dir / f"{node_id}.json")
    if raw is not None and "legacy_handler" in raw:
        ok_n, reason_n = verify_no_legacy_flip(
            node_id, handler_module, parity_executor=parity_executor
        )
        return ok_n, f"no-legacy: {reason_n}"

    ok_a, reason_a, sel_receipt = verify_adequacy_receipt(node_id, handler_module)
    if not ok_a:
        return False, f"adequacy: {reason_a}"

    ok_e, reason_e, sel_equiv = verify_equivalence_replay(node_id)
    ok_h, reason_h, sel_hand = verify_handflip_proof(
        node_id, handler_module, parity_executor=parity_executor
    )
    if not ok_e and not ok_h:
        return (
            False,
            f"proof: no equivalence-replay ({reason_e}) and no hand-flip proof "
            f"({reason_h})",
        )
    proof_reason, sel_proof = (reason_e, sel_equiv) if ok_e else (reason_h, sel_hand)

    # Bind coverage to the behavior proof: both must reference the same input set,
    # else a coverage-adequate golden could be replayed against an easier set.
    if set(sel_receipt) != set(sel_proof):
        return (
            False,
            "PAIR_INCOMPATIBLE: receipt/proof selected_input_hashes differ",
        )
    return True, f"{reason_a}+{proof_reason}"
