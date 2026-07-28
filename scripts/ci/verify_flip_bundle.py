# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fail-closed pre-PR seam gate for canonical-shape flips (OMN-14809, LANE c).

The canonical-shape CI ratchet (``scripts/ci/canonical_handler_shape.py``, OMN-14355)
is the *consuming* gate: it decides whether a non-canonical -> canonical baseline flip
carries valid proof. But the ratchet is structurally blind to a set of coherence holes
that only surface when the FIVE flip artifacts are checked jointly against live git,
the live handler source, and the full typed-receipt invariants. This gate RE-INVOKES
the real consuming gate (it imports ``canonical_handler_shape`` and calls
``verify_flip_receipt`` / ``classify_node`` / the git + baseline helpers — it does NOT
reimplement them) and adds seven fail-closed assertions per flipped node that close the
blind spots enumerated below. It mirrors the ratchet's fan-out CLI
(``--package`` / ``--src-root`` / ``--receipts-dir`` / ``--baseline``) so it points at
omnibase_infra / omnimarket identically.

Blind spots this gate closes (each = one assertion; first failure exits non-zero):

* **A1 — full typed-adequacy invariants.** ``verify_flip_receipt`` re-derives only ~10
  raw adequacy fields; it never constructs the full ``ModelAdequacyReceipt``, so the
  cross-field invariants (``selected_count == len(selected_input_hashes)``,
  ``meets_target == (pct >= target)``, waiver mutual-exclusion, degenerate-zero-input)
  are unchecked at gate time. Assertion 1 constructs ``ModelAdequacyReceipt(**raw)`` —
  any ``ValidationError`` FAILS.
* **(real verdict) — assertion 2** imports and calls the real ``verify_flip_receipt``,
  which transitively re-runs the adequacy re-hash, the equivalence/handflip proof, and
  the hash-set input binding. Must return ``ok=True``.
* **B5 — multi-handler partial flip.** ``classify_node`` keys on ``bindings[0]`` ONLY,
  so a node whose FIRST handler is canonical but a SECOND is not classifies canonical
  and silently partial-flips. Assertion 3 classifies EVERY binding from
  ``_contract_bindings`` and FAILS naming the offender if any binding is non-canonical.
* **B6 — no twin-baseline joint check.** The shape baseline (``NON_CANONICAL``) and the
  entrypoint baseline (``known_entrypointless``) are never checked together; a forgotten
  ``--update`` leaves the node in ``warn_baselined`` (silent, non-blocking). Assertion 4
  asserts the node is absent from BOTH baselines (post-update), that the shape baseline
  did not GROW vs origin/dev, and that the entrypoint-validator stale check is green for
  the node's handlers.
* **S1 — receipt minted before the final format.** ``handler_module_sha256`` is
  live-re-hashed at gate time, so a receipt minted BEFORE the final ``ruff format`` is
  stale the instant CI reformats. Assertion 5 asserts the live sha equals the recorded
  sha AND that a dry-run ``ruff format`` leaves the module unchanged (proving the receipt
  was minted post-format).
* **E1 — trusted, unreproduced equivalence golden.** ``verify_equivalence_replay``
  TRUSTS ``status == "pass"`` and never re-runs it. Assertion 6 (EQUIVALENCE path only —
  the hand-flip path is git-re-derived and exempt; and only for flips NEWLY added vs
  origin/dev — the two pre-existing merged flips are grandfathered) RERUNS the
  deterministic producer over the artifact's declared replay inputs and byte-compares its
  output against the committed artifact (see ``scripts/ci/equivalence_producer.py``).
  This replaces the identity-based independent-author attestation that first closed E1
  (omnibase_core#1472): identity is not evidence — any second git identity satisfies an
  author check while proving nothing — whereas byte-equality with a deterministic rerun
  proves the artifact is mechanically reproducible (OMN-14905).
* **P1 — parity tests that discriminate nothing.** Assertions 1-6 all grade artifacts
  against the HEAD tree; nothing here or anywhere else in CI ever executed a candidate
  test against the PRE-change tree, so "RED to GREEN for the right reason" was prose.
  A hand-flip proof could declare parity tests that are ALREADY GREEN at its own
  ``base_ref``. Assertion 7 (HAND-FLIP path only, NEW flips only) materializes that
  ``base_ref`` as a detached worktree, overlays the HEAD copies of the declared test
  files, and requires every declared id to fail there ON ITS OWN ASSERTION — a
  collection/import error is not RED, it is the same evidence as no test at all. A
  source-residency probe first proves the base worktree is what actually gets imported,
  so the verdict cannot be vacuous (OMN-15340, ``scripts/ci/parity_replay.py``).

Assertion 7 is forward-only by construction (NEW flips only), so the hand-flip receipts
already merged before it existed are outside it. That silence is itself a hole: a 2026-07-28
census that executed assertion 7 against every committed receipt with the newness rule
bypassed measured 21 of 22 FAILING (102 of 126 declared parity ids not
red-on-their-own-assertion at their own ``base_ref``). ``PARITY_RED_ON_BASE_DEBT`` in a
repo-local ``parity_red_on_base_baseline.py`` (OMN-15344) names that population explicitly
and makes it SHRINK-ONLY: growth hard-fails, an entry naming a receipt that does not exist
hard-fails, and REMOVING an entry re-arms assertion 7 for that node — a burn-down is a claim
the gate executes, not a line you delete. A frozen list is honest debt; silence is not.

Usage (pre-commit / CI, mirrors canonical_handler_shape)::

    uv run python scripts/ci/verify_flip_bundle.py                    # omnibase_core
    uv run python scripts/ci/verify_flip_bundle.py --package omnibase_infra \\
        --src-root ../omnibase_infra/src \\
        --receipts-dir ../omnibase_infra/scripts/ci/adequacy_receipts \\
        --baseline ../omnibase_infra/scripts/ci/canonical_handler_shape_baseline.py

The gate discovers the nodes NEWLY flipped in this PR (removed from ``NON_CANONICAL``
vs origin/dev and canonical now, or carrying a newly-added adequacy receipt) and runs
all seven assertions on each. Zero flips -> exit 0 (nothing to prove; the ratchet already
guards new non-canonical nodes). Any assertion failure -> exit 1.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# Re-invoke the REAL consuming gate + the canonical typed adequacy model. Dual import so
# the module works both as ``scripts.ci.verify_flip_bundle`` (pytest, repo root on path)
# and as a standalone ``python scripts/ci/verify_flip_bundle.py`` (script dir on path).
try:  # pragma: no cover - import shim
    from scripts.ci import canonical_handler_shape as chs
    from scripts.ci import equivalence_producer as eqp
    from scripts.ci import parity_replay as prp
    from scripts.ci.adequacy_receipt import ModelAdequacyReceipt
except ImportError:  # pragma: no cover - script-dir invocation
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import canonical_handler_shape as chs  # type: ignore[import-not-found, no-redef]
    import equivalence_producer as eqp  # type: ignore[import-not-found, no-redef]
    import parity_replay as prp  # type: ignore[import-not-found, no-redef]
    from adequacy_receipt import (  # type: ignore[import-not-found, no-redef]
        ModelAdequacyReceipt,
    )

# The two flips that merged BEFORE this gate existed. Assertion 6 (deterministic
# producer rerun + byte-compare) is a forward-looking seam: an already-merged v1 golden
# carries no replay declaration and so cannot be reproduced, so these are grandfathered (skipped for assertion 6 only — all
# other assertions still apply). The general newness rule (proof artifact absent at the
# git base) also covers them; this constant is belt-and-suspenders per OMN-14809.
GRANDFATHERED_FLIPS: frozenset[str] = frozenset(
    {
        "omnibase_infra.nodes.node_coding_agent_invoke_effect",
        "omnibase_infra.nodes.node_coding_agent_workspace_compute",
    }
)

DEFAULT_BASE_REF = "origin/dev"

# Repo-local parity-debt baseline (OMN-15344). Resolved BY CONVENTION beside whatever
# canonical_handler_shape baseline the caller points at, deliberately NOT via a required
# new flag: the per-repo CI wiring that consumes this gate (omnibase_infra / omnimarket)
# pins omnibase_core at a moving ref, so a required flag would make the pair landable in
# exactly one order. An ABSENT file is legal and means "no declared debt" — byte-for-byte
# today's behavior — which is what keeps both sides green before AND after either lands.
PARITY_BASELINE_FILENAME = "parity_red_on_base_baseline.py"
PARITY_BASELINE_SYMBOL = "PARITY_RED_ON_BASE_DEBT"

# Candidate (validator, baseline) locations for the per-repo entrypoint-dispatch gate
# (``omnibase_infra.validators.handler_dispatch_entrypoint`` + its known_entrypointless
# baseline). The layout differs per repo (infra uses src/ + config/validation/;
# omnimarket is a flat package). ``{pkg}`` is substituted with the target package.
_ENTRYPOINT_VALIDATOR_RELPATHS: tuple[str, ...] = (
    "src/{pkg}/validators/handler_dispatch_entrypoint.py",
    "{pkg}/validators/handler_dispatch_entrypoint.py",
)
_ENTRYPOINT_BASELINE_RELPATHS: tuple[str, ...] = (
    "config/validation/handler_dispatch_entrypoint_baseline.yaml",
    "validation/handler_dispatch_entrypoint_baseline.yaml",
)


# --------------------------------------------------------------------------- #
# Typed result models
# --------------------------------------------------------------------------- #


class ModelAssertionOutcome(BaseModel):
    """One assertion's result within a flip-bundle verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    index: int
    name: str
    ok: bool
    detail: str


class ModelFlipBundleResult(BaseModel):
    """The joint verdict over one node's flip artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    node_id: str
    ok: bool
    failed_assertion: int | None
    grandfathered: bool
    outcomes: tuple[ModelAssertionOutcome, ...]
    reason: str


# --------------------------------------------------------------------------- #
# Scope + small git primitives (generic; the gate-specific git helpers are reused
# from canonical_handler_shape — _git_repo_root / _git_show / _git_ref_exists).
# --------------------------------------------------------------------------- #


def _apply_scope(
    package: str,
    src_root: Path | None,
    receipts_dir: Path | None,
    baseline: Path | None,
) -> tuple[Path, str, Path, Path]:
    """Point the imported ratchet at ``package`` exactly as its ``main()`` does.

    ``classify_node`` / ``verify_flip_receipt`` / ``_resolve_module_file`` read module
    globals; setting them here (via the ratchet's own pure ``_resolve_scope``) makes
    every re-invoked function operate on the target package's tree/receipts/baseline.
    """
    s_src, s_glob, s_base, s_recv = chs._resolve_scope(
        package, src_root, None, baseline, receipts_dir
    )
    chs.PACKAGE = package
    chs.SRC_ROOT = s_src
    chs.NODES_GLOB = s_glob
    chs.BASELINE_PATH = s_base
    chs.RECEIPTS_DIR = s_recv
    return s_src, s_glob, s_base, s_recv


def _resolve_parity_baseline(baseline_path: Path, override: Path | None) -> Path:
    """Convention-resolved path to the target repo's parity-debt baseline."""
    if override is not None:
        return override
    return baseline_path.parent / PARITY_BASELINE_FILENAME


def _parse_symbol_tuple(source: str, symbol: str) -> tuple[str, ...]:
    """Read a module-level ``symbol = (...)`` literal out of Python SOURCE.

    AST-parsed, never exec'd: the base-ref copy comes straight out of ``git show`` and
    must not be executable input. Mirrors ``canonical_handler_shape._parse_non_canonical``.
    """
    for node in ast.parse(source).body:
        targets: list[str] = []
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        if symbol in targets and value is not None:
            return tuple(str(item) for item in ast.literal_eval(value))
    return ()


def load_parity_baseline(path: Path) -> tuple[str, ...]:
    """Working-tree parity-debt entries. ABSENT file -> ``()`` (no debt declared).

    Unparseable is NOT empty: a baseline the gate cannot read is a gate that silently
    stops enforcing, so it raises and the caller fails closed.
    """
    if not path.exists():
        return ()
    try:
        return _parse_symbol_tuple(
            path.read_text(encoding="utf-8"), PARITY_BASELINE_SYMBOL
        )
    except (OSError, SyntaxError, ValueError) as exc:
        raise ValueError(f"parity baseline at {path} is unparseable: {exc}") from exc


def load_base_parity_baseline(
    path: Path, base_ref: str
) -> tuple[tuple[str, ...] | None, bool]:
    """Parity-debt entries as of ``base_ref``, plus whether the file EXISTED there.

    Returns ``(entries, existed_at_base)``:

    * ``(entries, True)``  — the baseline was present at the base; shrink-only is live.
    * ``((), False)``      — the file is NEW in this change. Growth is not a meaningful
      comparison there (every entry would be growth, so the seeding commit would fail
      itself); the caller applies the seeding rule instead.
    * ``(None, False)``    — git cannot answer at all, which disables the comparison for
      that run, the same diff-unavailable tolerance the shape ratchet already carries.
      In CI the PR base is always present, so it is live there.
    """
    anchor = path if path.exists() else path.parent
    repo_root = chs._git_repo_root(anchor)
    if repo_root is None or not chs._git_ref_exists(repo_root, base_ref):
        return None, False
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None, False
    source = chs._git_show(repo_root, base_ref, str(rel).replace(os.sep, "/"))
    if source is None:
        return (), False
    try:
        return _parse_symbol_tuple(source, PARITY_BASELINE_SYMBOL), True
    except (SyntaxError, ValueError):
        return None, False


def _git_added_files(repo_root: Path, base_ref: str) -> list[str] | None:
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--name-only",
                "--diff-filter=A",
                f"{base_ref}...HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Assertion 1 — full typed adequacy invariants (closes A1)
# --------------------------------------------------------------------------- #


def _assert_typed_adequacy(node_id: str, receipts_dir: Path) -> tuple[bool, str]:
    path = receipts_dir / f"{node_id}.json"
    if not path.exists():
        return False, f"adequacy receipt absent at {path}"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"adequacy receipt unparseable: {exc}"
    if not isinstance(raw, dict):
        return False, "adequacy receipt is not a JSON object"
    try:
        ModelAdequacyReceipt(**raw)
    except Exception as exc:  # pydantic ValidationError et al. => FAIL (BLE001 ignored)
        return False, f"ModelAdequacyReceipt invariants violated: {exc}"
    return True, "full ModelAdequacyReceipt cross-field invariants hold"


# --------------------------------------------------------------------------- #
# Assertion 2 — real consuming-gate verdict (re-invoke, do not reimplement)
# --------------------------------------------------------------------------- #


def _assert_real_gate_verdict(
    node_id: str, handler_module: str | None
) -> tuple[bool, str]:
    ok, reason = chs.verify_flip_receipt(node_id, handler_module)
    return ok, f"verify_flip_receipt -> {reason}"


# --------------------------------------------------------------------------- #
# Assertion 3 — full-node canonicality across ALL bindings (closes B5)
# --------------------------------------------------------------------------- #


def _classify_binding(module: str, cls: str | None, node_pkg: str) -> tuple[bool, str]:
    """Classify ONE contract binding using the ratchet's own resolver primitives."""
    resolved_module = module or node_pkg
    files = chs._module_to_files(resolved_module)
    fn, cdef, path = chs._resolve_handler(files, cls)
    label = f"{resolved_module}:{cls or '<any>'}"
    if cdef is None:
        return False, f"{label} unresolved (phantom/no_binding)"
    if fn is None:
        opm = chs._operation_methods(cdef)
        kind = f"op_method({opm[:3]})" if opm else "empty"
        return False, f"{label} has no handle() [{kind}]"
    adaptable, reason = chs._handle_is_adaptable(fn)
    if not adaptable:
        return False, f"{label} nonadaptable ({reason})"
    mod_text = path.read_text(encoding="utf-8") if path and path.exists() else ""
    if "ModelEventEnvelope" in mod_text:
        return False, f"{label} references ModelEventEnvelope (envelope_in_core)"
    return True, f"{label} canonical ({reason})"


def _assert_full_node_canonical(
    contract_path: Path, data: dict[str, object]
) -> tuple[bool, str]:
    node_pkg = chs._node_package(contract_path)
    bindings = chs._contract_bindings(data)
    if not bindings:
        return False, "contract declares no handler binding"
    offenders: list[str] = []
    for module, cls in bindings:
        ok, reason = _classify_binding(module, cls, node_pkg)
        if not ok:
            offenders.append(reason)
    if offenders:
        return (
            False,
            f"multi-handler partial flip: {len(offenders)}/{len(bindings)} binding(s) "
            f"non-canonical -> {'; '.join(offenders)}",
        )
    return True, f"all {len(bindings)} binding(s) classify canonical"


# --------------------------------------------------------------------------- #
# Assertion 4 — twin-baseline shrink + entrypoint stale check (closes B6)
# --------------------------------------------------------------------------- #


def _load_entrypoint_validator(
    target_root: Path, package: str
) -> tuple[object, Path] | None:
    """Load the target repo's real entrypoint-dispatch validator, standalone.

    Returns ``(module, baseline_path)`` when the repo HAS the entrypoint gate, else
    None (the repo genuinely has no such invariant — e.g. omnibase_core). Loading by
    file path never triggers the target package's ``__init__`` (the validator imports
    only stdlib + yaml), so no cross-repo runtime deps are pulled in. The module MUST be
    registered in ``sys.modules`` before ``exec_module`` because it defines a
    ``slots=True`` dataclass whose creation looks itself up there.
    """
    val_path: Path | None = None
    for rel in _ENTRYPOINT_VALIDATOR_RELPATHS:
        cand = target_root / rel.format(pkg=package)
        if cand.exists():
            val_path = cand
            break
    if val_path is None:
        return None
    baseline_path: Path | None = None
    for rel in _ENTRYPOINT_BASELINE_RELPATHS:
        cand = target_root / rel
        if cand.exists():
            baseline_path = cand
            break
    mod_name = f"_verify_flip_bundle_hde_{package}"
    spec = importlib.util.spec_from_file_location(mod_name, val_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    # baseline_path may be None here -> caller FAILS closed (validator present, no baseline)
    return module, baseline_path if baseline_path is not None else Path("<missing>")


def _assert_twin_baseline(
    node_id: str,
    contract_path: Path,
    baseline_path: Path,
    base_ref: str,
    target_root: Path,
    src_root: Path,
    package: str,
) -> tuple[bool, str]:
    # 4a: node absent from the working (post-update) NON_CANONICAL baseline.
    working = set(chs.load_baseline(baseline_path))
    if node_id in working:
        return (
            False,
            f"node still in NON_CANONICAL baseline ({baseline_path.name}) — the flip is "
            f"a silent warn_baselined; run canonical_handler_shape.py --update",
        )
    # 4c: monotonic non-increasing — the shape baseline must not have GROWN vs base.
    base = chs.load_base_baseline(baseline_path, base_ref)
    if base is None:
        return False, f"cannot resolve base baseline at {base_ref} (fail-closed)"
    growth = sorted(set(working) - set(base))
    if growth:
        return (
            False,
            f"NON_CANONICAL grew vs {base_ref} (must be shrink-only): {growth[:5]}",
        )
    # 4b + 4d: entrypoint twin baseline — the node's contract-declared handlers must be
    # absent from known_entrypointless. Because stale ⊆ baseline, a node absent from the
    # baseline cannot be a stale entry; and a canonical def-B handler necessarily exposes
    # handle(), so removing it was justified. Re-invoke the REAL validator's YAML-only
    # functions (load_baseline / declared_handlers) — no handler import.
    ep = _load_entrypoint_validator(target_root, package)
    if ep is None:
        return (
            True,
            f"absent from NON_CANONICAL; no baseline growth; "
            f"{package} has no entrypoint-dispatch validator (n/a)",
        )
    val_mod, ep_baseline_path = ep
    if not ep_baseline_path.exists():
        return (
            False,
            "entrypoint-dispatch validator present but its known_entrypointless "
            "baseline is missing (misconfigured repo)",
        )
    ep_baseline = val_mod.load_baseline(ep_baseline_path)  # type: ignore[attr-defined]
    node_dir = src_root / node_id.replace(".", "/")
    declared = val_mod.declared_handlers(node_dir)  # type: ignore[attr-defined]
    listed = [d.key for d in declared if d.key in ep_baseline]
    if listed:
        return (
            False,
            f"node handler(s) still in known_entrypointless (twin baseline not shrunk / "
            f"stale): {listed}",
        )
    return (
        True,
        f"absent from NON_CANONICAL; no baseline growth; {len(declared)} handler(s) "
        f"absent from known_entrypointless (stale-free)",
    )


# --------------------------------------------------------------------------- #
# Assertion 5 — ordering seam: receipt minted post-format (closes S1)
# --------------------------------------------------------------------------- #


def _ruff_format_clean(module_file: Path, cwd: Path) -> tuple[bool, str]:
    """Dry-run ``ruff format`` (``--check``): exit 0 == already formatted (unchanged).

    ``--check`` is ruff's dry-run format; a clean result proves a real ``ruff format``
    would leave the module byte-identical, so its sha (== recorded, per 5a) is stable.
    A would-reformat result means the recorded sha was minted BEFORE the final format.
    Missing/errored ruff -> fail-closed.
    """
    for argv in (
        ["ruff", "format", "--check", str(module_file)],
        ["uv", "run", "ruff", "format", "--check", str(module_file)],
    ):
        try:
            proc = subprocess.run(
                argv, cwd=str(cwd), capture_output=True, text=True, check=False
            )
        except OSError:
            continue
        if proc.returncode == 0:
            return True, "ruff format --check clean (module already formatted)"
        if proc.returncode == 1:
            return False, "ruff format --check reports the module would be reformatted"
        # returncode 2 (ruff internal/parse error) -> try the next launcher.
    return False, "ruff unavailable or errored (fail-closed)"


def _assert_ordering_seam(
    node_id: str, receipts_dir: Path, target_root: Path
) -> tuple[bool, str]:
    raw = chs._load_json(receipts_dir / f"{node_id}.json")
    if raw is None:
        return False, "adequacy receipt unreadable for ordering check"
    recorded = raw.get("handler_module_sha256")
    module = raw.get("handler_module")
    if not isinstance(module, str) or not module:
        return False, "receipt has no handler_module for the ordering check"
    module_file = chs._resolve_module_file(module)
    if module_file is None:
        return False, f"handler_module {module} not resolvable"
    live = chs._sha256_file(module_file)
    if live != recorded:
        return (
            False,
            f"live handler_module sha256 != recorded (5a): {live} != {recorded}",
        )
    ok_fmt, detail = _ruff_format_clean(module_file, target_root)
    if not ok_fmt:
        return False, f"receipt minted PRE-format (S1): {detail}"
    return (
        True,
        "live sha == recorded and ruff-format-clean (receipt minted post-format)",
    )


# --------------------------------------------------------------------------- #
# Assertion 6 — deterministic producer rerun + byte-compare (closes E1, OMN-14905)
# --------------------------------------------------------------------------- #
#
# The seam a NEW equivalence artifact must carry is a DECLARATION of the replay inputs
# (see ``equivalence_producer.REQUIRED_DECLARATION_KEYS``) — never a verdict and never an
# identity:
#
#   "receipt_schema": "equivalence_replay.v2",
#   "declaration": {
#       "base_ref":                  "<pre-flip commit; must be an ancestor of the gate base>",
#       "legacy_handler_module":     "<dotted module read out of git at base_ref>",
#       "legacy_handler_symbol":     "<class>",   "legacy_entrypoint":   "<def-A method>",
#       "canonical_handler_module":  "<dotted module in the working tree>",
#       "canonical_handler_symbol":  "<class>",   "canonical_entrypoint": "<def-B method>",
#       "input_model":               "<dotted Module.Class of the request model>",
#       "replay_inputs":             ["<repo-relative input .json>", ...],
#       "volatile_mask":             ["<dotted path>", ...]
#   }
#
# The gate then RERUNS the producer over exactly those inputs — executing the HEAD
# canonical handler against the legacy handler materialized from ``git show`` — derives
# ``selected_input_hashes`` and ``status`` itself, and byte-compares the re-emitted
# artifact against the one the PR carries.
#
# This REPLACES the prior independent-author attestation (omnibase_core#1472). That
# assertion required ``provenance.authored_by != git-author(def_b_commit)``, which is an
# identity property: a bot, a second machine, or a co-author trailer satisfies it while
# proving nothing about the artifact, and it never re-executed the replay it gated.
# Byte-equality with a deterministic rerun proves the artifact is mechanically
# reproducible; who authored it is irrelevant, which is the point.


def _assert_reproducible_equivalence(
    node_id: str,
    receipts_dir: Path,
    repo_root: Path,
    src_root: Path,
    base_ref: str,
) -> tuple[bool, str]:
    return eqp.byte_compare(
        node_id,
        receipts_dir / f"{node_id}{chs.EQUIVALENCE_SUFFIX}",
        repo_root,
        src_root,
        base_ref,
    )


def _flip_proof_is_new(
    node_id: str,
    receipts_dir: Path,
    repo_root: Path,
    base_ref: str,
    suffix: str | None = None,
) -> bool:
    """A flip is NEW when its proof artifact is ABSENT at the git base.

    Fail-closed: any inability to prove the artifact PRE-EXISTED at the base (artifact
    outside the repo, base unresolvable) returns True -> the assertion is applied.
    """
    art = receipts_dir / f"{node_id}{suffix or chs.EQUIVALENCE_SUFFIX}"
    try:
        rel = art.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True
    if not chs._git_ref_exists(repo_root, base_ref):
        return True
    src = chs._git_show(repo_root, base_ref, str(rel).replace(os.sep, "/"))
    return src is None


# --------------------------------------------------------------------------- #
# Assertion 7 — declared parity tests RED on the receipt's own base_ref (OMN-15340)
# --------------------------------------------------------------------------- #
#
# Assertions 1-6 all grade artifacts against the HEAD tree. None of them — and no
# other mechanism in CI — ever executed a candidate test against the PRE-change tree,
# so "RED to GREEN for the right reason" was prose. A hand-flip proof can therefore
# declare parity tests that are ALREADY GREEN at ``base_ref``: they run, they pass,
# they discriminate nothing, and the flip is credited with a behavior proof it never
# earned.
#
# Assertion 7 materializes the receipt's OWN ``base_ref`` as a detached worktree,
# overlays the HEAD copies of the declared test files onto that pre-change tree, and
# requires EVERY declared id to fail there ON ITS OWN ASSERTION. Exit reasons are
# distinguished, never collapsed into "non-zero": a collection/import error means the
# test cannot even run against the old code, which is exactly as much evidence as no
# test at all (``feedback_prove_red_against_exists_but_wrong``). Before any of that
# counts, a residency probe proves the base worktree's source is what actually gets
# imported — otherwise an editable install silently grades HEAD and every verdict,
# RED or GREEN, is vacuous.


def _assert_parity_red_on_base(
    node_id: str,
    receipts_dir: Path,
    repo_root: Path,
    src_root: Path,
) -> tuple[bool, str]:
    raw = chs._load_json(receipts_dir / f"{node_id}{chs.HANDFLIP_SUFFIX}")
    if raw is None:
        return False, "hand-flip proof unreadable for the parity RED-on-base check"
    parity = raw.get("parity")
    if not isinstance(parity, dict):
        return False, "hand-flip proof missing parity block"
    test_ids_raw = parity.get("test_ids")
    if not isinstance(test_ids_raw, list) or not test_ids_raw:
        return False, "hand-flip parity block names no test_ids to execute"
    base_ref = raw.get("base_ref")
    if not isinstance(base_ref, str) or not base_ref:
        return False, "hand-flip proof missing base_ref"
    legacy_module = raw.get("legacy_handler_module") or raw.get(
        "canonical_handler_module"
    )
    if not isinstance(legacy_module, str) or not legacy_module:
        return False, "hand-flip proof names no module for the residency probe"
    return prp.red_on_base(
        node_id,
        tuple(str(t) for t in test_ids_raw),
        base_ref,
        legacy_module,
        repo_root,
        src_root,
    )


# --------------------------------------------------------------------------- #
# Parity-debt SHRINK-ONLY ratchet (OMN-15344)
# --------------------------------------------------------------------------- #
#
# Three rules, all fail-closed:
#
#   GROWTH   adding a node id is a hard fail. A new hand-flip may not be baselined out
#            of assertion 7 — that is the entire thing assertion 7 exists to stop.
#   STALE    an entry naming a hand-flip proof that does not exist at HEAD is a hard
#            fail, so the list cannot rot into decoration and cannot be pre-seeded with
#            a node id ahead of the PR that would smuggle its receipt in.
#   REMOVAL  dropping an entry is a CLAIM that the node now passes, and the gate
#            EXECUTES it: assertion 7 is re-armed for exactly that node and must pass.
#            Removing the entry by deleting the hand-flip proof instead fails too.
#   SEEDING  the commit that CREATES the file cannot be judged by growth — every entry
#            would be growth and the seeding commit would fail itself. It is instead
#            held to the rule that actually matters: a seed may contain only
#            ALREADY-MERGED debt. A flip that is new in the same PR cannot be born
#            baselined, so the one-time exemption buys no cover for a new flip. This
#            path is unreachable a second time: once the file exists at the base, every
#            later change is judged by growth/removal.
#
# The ratchet deliberately does NOT re-execute the whole baselined population on every
# run: the 2026-07-28 census cost ~24 minutes of pytest for 22 receipts. Steady-state
# cost here is a git-show plus a set comparison; real pytest is paid only when a
# burn-down is claimed.
#
# ``RED_EXCEPTION`` stays inadmissible. ``parity_replay`` counts only ``RED_ASSERTION``,
# and nothing in this ratchet adds an admissibility path — an exception at the base tree
# is indistinguishable from a test that is merely incompatible with the old code, which
# is not a discriminating claim. Admitting it is what would make most of this debt
# evaporate without a single test getting better.


def _parity_debt_ratchet(
    working: tuple[str, ...],
    base: tuple[str, ...] | None,
    base_existed: bool,
    receipts_dir: Path,
    repo_root: Path | None,
    src_root: Path,
    base_ref: str,
) -> list[str]:
    """Enforce shrink-only on the parity-debt baseline; returns violation strings."""
    errors: list[str] = []
    working_set = set(working)

    for node_id in sorted(working_set):
        art = receipts_dir / f"{node_id}{chs.HANDFLIP_SUFFIX}"
        if not art.exists():
            errors.append(
                f"{node_id}: STALE entry in {PARITY_BASELINE_FILENAME} — it names a "
                f"hand-flip proof that does not exist at HEAD ({art}). Remove the entry; "
                f"the baseline may not carry ids without a receipt."
            )

    if base is None:
        return errors

    if not base_existed:
        for node_id in sorted(working_set):
            if repo_root is None or _flip_proof_is_new(
                node_id, receipts_dir, repo_root, base_ref, chs.HANDFLIP_SUFFIX
            ):
                errors.append(
                    f"{node_id}: seeded into a NEW {PARITY_BASELINE_FILENAME}, but its "
                    f"hand-flip proof is NEW in this change. The baseline may only be "
                    f"seeded with already-merged debt — a new flip must pass assertion 7."
                )
        return errors

    base_set = set(base)

    for node_id in sorted(working_set - base_set):
        errors.append(
            f"{node_id}: ADDED to {PARITY_BASELINE_FILENAME} — the parity-debt baseline "
            f"is SHRINK-ONLY. A new hand-flip must declare parity tests that are RED on "
            f"their own assertion at its base_ref; it may not be baselined out of "
            f"assertion 7."
        )

    for node_id in sorted(base_set - working_set):
        art = receipts_dir / f"{node_id}{chs.HANDFLIP_SUFFIX}"
        if not art.exists():
            if repo_root is not None and not _flip_proof_is_new(
                node_id, receipts_dir, repo_root, base_ref, chs.HANDFLIP_SUFFIX
            ):
                errors.append(
                    f"{node_id}: removed from {PARITY_BASELINE_FILENAME} by DELETING its "
                    f"hand-flip proof (present at {base_ref}, absent at HEAD). Burning "
                    f"down parity debt means making the declared tests discriminate, not "
                    f"deleting the proof that records that they do not."
                )
            continue
        if repo_root is None:
            errors.append(
                f"{node_id}: removed from {PARITY_BASELINE_FILENAME}, but the git repo "
                f"root is unresolvable so the burn-down claim cannot be EXECUTED "
                f"(fail-closed)."
            )
            continue
        ok, detail = _assert_parity_red_on_base(
            node_id, receipts_dir, repo_root, src_root
        )
        if not ok:
            errors.append(
                f"{node_id}: removed from {PARITY_BASELINE_FILENAME}, but assertion 7 "
                f"still FAILS when executed -> {detail}"
            )
    return errors


# --------------------------------------------------------------------------- #
# Orchestration: run the seven assertions in order, stop at first failure.
# --------------------------------------------------------------------------- #


def verify_flip_bundle(
    node_id: str,
    package: str,
    src_root: Path | None,
    receipts_dir: Path | None,
    baseline: Path | None,
    base_ref: str = DEFAULT_BASE_REF,
    parity_baseline: frozenset[str] = frozenset(),
) -> ModelFlipBundleResult:
    """Verify one node's flip artifacts jointly. Fail-closed, first-failure-wins.

    Absence, unparseability, a None from any git probe, or an import failure all
    evaluate to FAIL (never SKIP). Runs the seven assertions in numeric order and stops at
    the first failure so a seeded defect surfaces on its intended assertion, not
    incidentally on a later one. Snapshots + restores the ratchet's module globals so a
    fan-out call leaves no scope state behind for other callers/tests.
    """
    saved = (
        chs.PACKAGE,
        chs.SRC_ROOT,
        chs.NODES_GLOB,
        chs.BASELINE_PATH,
        chs.RECEIPTS_DIR,
    )
    try:
        return _verify_flip_bundle_impl(
            node_id,
            package,
            src_root,
            receipts_dir,
            baseline,
            base_ref,
            parity_baseline,
        )
    finally:
        (
            chs.PACKAGE,
            chs.SRC_ROOT,
            chs.NODES_GLOB,
            chs.BASELINE_PATH,
            chs.RECEIPTS_DIR,
        ) = saved


def _verify_flip_bundle_impl(
    node_id: str,
    package: str,
    src_root: Path | None,
    receipts_dir: Path | None,
    baseline: Path | None,
    base_ref: str,
    parity_baseline: frozenset[str] = frozenset(),
) -> ModelFlipBundleResult:
    s_src, _glob, s_base, s_recv = _apply_scope(
        package, src_root, receipts_dir, baseline
    )
    repo_root = chs._git_repo_root(s_src)
    target_root = repo_root if repo_root is not None else s_src.parent
    contract_path = s_src / node_id.replace(".", "/") / "contract.yaml"

    outcomes: list[ModelAssertionOutcome] = []

    def _record(index: int, name: str, ok: bool, detail: str) -> ModelFlipBundleResult:
        outcomes.append(
            ModelAssertionOutcome(index=index, name=name, ok=ok, detail=detail)
        )
        return ModelFlipBundleResult(
            node_id=node_id,
            ok=False,
            failed_assertion=index,
            grandfathered=grandfathered,
            outcomes=tuple(outcomes),
            reason=f"assertion {index} ({name}) FAILED: {detail}",
        )

    grandfathered = False

    # Preconditions the later assertions rely on: a readable contract + its bindings.
    if not contract_path.exists():
        return _record(0, "preflight", False, f"contract absent at {contract_path}")
    data = chs.yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return _record(0, "preflight", False, "contract is not a mapping")
    finding = chs.classify_node(contract_path)
    handler_module = finding.handler_module

    # Assertion 1 — full typed adequacy invariants (A1)
    ok, detail = _assert_typed_adequacy(node_id, s_recv)
    if not ok:
        return _record(1, "typed-adequacy", ok, detail)
    outcomes.append(
        ModelAssertionOutcome(index=1, name="typed-adequacy", ok=True, detail=detail)
    )

    # Assertion 2 — real consuming-gate verdict
    ok, detail = _assert_real_gate_verdict(node_id, handler_module)
    if not ok:
        return _record(2, "real-gate-verdict", ok, detail)
    outcomes.append(
        ModelAssertionOutcome(index=2, name="real-gate-verdict", ok=True, detail=detail)
    )

    # Assertion 3 — full-node canonicality across ALL bindings (B5)
    ok, detail = _assert_full_node_canonical(contract_path, data)
    if not ok:
        return _record(3, "full-node-canonical", ok, detail)
    outcomes.append(
        ModelAssertionOutcome(
            index=3, name="full-node-canonical", ok=True, detail=detail
        )
    )

    # Assertion 4 — twin-baseline shrink + entrypoint stale check (B6)
    ok, detail = _assert_twin_baseline(
        node_id, contract_path, s_base, base_ref, target_root, s_src, package
    )
    if not ok:
        return _record(4, "twin-baseline-shrink", ok, detail)
    outcomes.append(
        ModelAssertionOutcome(
            index=4, name="twin-baseline-shrink", ok=True, detail=detail
        )
    )

    # Assertion 5 — ordering seam: receipt minted post-format (S1)
    ok, detail = _assert_ordering_seam(node_id, s_recv, target_root)
    if not ok:
        return _record(5, "ordering-seam", ok, detail)
    outcomes.append(
        ModelAssertionOutcome(index=5, name="ordering-seam", ok=True, detail=detail)
    )

    # Assertion 6 — deterministic producer rerun + byte-compare (E1), equivalence +
    # new-flip only.
    ok_e = chs.verify_equivalence_replay(node_id)[0]
    if not ok_e:
        detail6 = "hand-flip proof path — verbatim-preservation git-re-derived; exempt"
    elif repo_root is None:
        # Equivalence path but no git to establish newness / rerun the legacy side.
        return _record(
            6,
            "reproducible-equivalence",
            False,
            "cannot resolve git repo root to establish flip newness / rerun the "
            "producer (E1)",
        )
    elif node_id in GRANDFATHERED_FLIPS or not _flip_proof_is_new(
        node_id, s_recv, repo_root, base_ref
    ):
        grandfathered = True
        detail6 = "grandfathered — equivalence proof pre-existing at base (not new vs origin/dev)"
    else:
        ok6, detail6 = _assert_reproducible_equivalence(
            node_id, s_recv, repo_root, s_src, base_ref
        )
        if not ok6:
            return _record(6, "reproducible-equivalence", False, detail6)
    outcomes.append(
        ModelAssertionOutcome(
            index=6, name="reproducible-equivalence", ok=True, detail=detail6
        )
    )

    # Assertion 7 — declared parity tests RED-on-their-own-assertion at the receipt's
    # own base_ref (OMN-15340). Hand-flip path only: the equivalence path carries no
    # parity block and is covered by assertion 6's deterministic rerun.
    handflip_path = s_recv / f"{node_id}{chs.HANDFLIP_SUFFIX}"
    if not handflip_path.exists():
        detail7 = (
            "equivalence proof path — no hand-flip parity block to execute "
            "(assertion 6 covers reproducibility)"
        )
    elif node_id in parity_baseline:
        grandfathered = True
        detail7 = (
            f"baselined parity debt ({PARITY_BASELINE_FILENAME}) — assertion 7 NOT "
            f"credited for this node; the entry is shrink-only and removing it re-arms "
            f"the executed check"
        )
    elif repo_root is None:
        return _record(
            7,
            "parity-red-on-base",
            False,
            "cannot resolve git repo root to materialize the receipt's base_ref",
        )
    elif not _flip_proof_is_new(
        node_id, s_recv, repo_root, base_ref, chs.HANDFLIP_SUFFIX
    ):
        grandfathered = True
        detail7 = (
            "grandfathered — hand-flip proof pre-existing at base (not new vs "
            f"{base_ref})"
        )
    else:
        ok7, detail7 = _assert_parity_red_on_base(node_id, s_recv, repo_root, s_src)
        if not ok7:
            return _record(7, "parity-red-on-base", False, detail7)
    outcomes.append(
        ModelAssertionOutcome(
            index=7, name="parity-red-on-base", ok=True, detail=detail7
        )
    )

    return ModelFlipBundleResult(
        node_id=node_id,
        ok=True,
        failed_assertion=None,
        grandfathered=grandfathered,
        outcomes=tuple(outcomes),
        reason="all seven flip-bundle assertions hold",
    )


# --------------------------------------------------------------------------- #
# CLI — discover this PR's newly-flipped nodes and verify each bundle.
# --------------------------------------------------------------------------- #


def _newly_flipped_nodes(
    src_root: Path,
    baseline_path: Path,
    receipts_dir: Path,
    base_ref: str,
) -> list[str] | None:
    """Nodes flipped non-canonical -> canonical in THIS PR (vs ``base_ref``).

    Signals (union): (1) removed from ``NON_CANONICAL`` vs base AND canonical now;
    (2) an adequacy receipt newly added vs base AND canonical now. Returns None when the
    git base is unavailable (caller notes + exits 0, matching the ratchet's tolerance —
    the ratchet itself still hard-guards new non-canonical nodes on that run).
    """
    working = set(chs.load_baseline(baseline_path))
    base = chs.load_base_baseline(baseline_path, base_ref)
    if base is None:
        return None
    flips: set[str] = set()
    for node_id in set(base) - working:
        contract = src_root / node_id.replace(".", "/") / "contract.yaml"
        if contract.exists() and chs.classify_node(contract).is_canonical:
            flips.add(node_id)
    repo_root = chs._git_repo_root(src_root)
    if repo_root is not None:
        added = _git_added_files(repo_root, base_ref)
        try:
            recv_rel = receipts_dir.resolve().relative_to(repo_root.resolve())
        except ValueError:
            recv_rel = None
        if added is not None and recv_rel is not None:
            prefix = str(recv_rel).replace(os.sep, "/") + "/"
            for rel in added:
                name = rel.split("/")[-1]
                if not rel.startswith(prefix) or not name.endswith(".json"):
                    continue
                if name.endswith((".equivalence.json", ".handflip.json")):
                    continue
                node_id = name[: -len(".json")]
                contract = src_root / node_id.replace(".", "/") / "contract.yaml"
                if contract.exists() and chs.classify_node(contract).is_canonical:
                    flips.add(node_id)
    return sorted(flips)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed pre-PR seam gate for canonical-shape flips (OMN-14809)."
    )
    parser.add_argument(
        "--package",
        default=os.environ.get("ONEX_CANON_SHAPE_PACKAGE", "omnibase_core"),
        help="Target package to verify (fan-out; defaults to omnibase_core).",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        default=(
            Path(os.environ["ONEX_CANON_SHAPE_SRC_ROOT"])
            if "ONEX_CANON_SHAPE_SRC_ROOT" in os.environ
            else None
        ),
        help="Source root containing --package's node tree (defaults to this repo's src/).",
    )
    parser.add_argument(
        "--receipts-dir",
        type=Path,
        default=None,
        help="Override the adequacy-receipts directory for --package.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Override the canonical_handler_shape baseline module path for --package.",
    )
    parser.add_argument(
        "--parity-baseline",
        type=Path,
        default=None,
        help=(
            f"Override the parity-debt baseline path (default: {PARITY_BASELINE_FILENAME} "
            f"beside --baseline)."
        ),
    )
    parser.add_argument(
        "--base-ref",
        default=DEFAULT_BASE_REF,
        help="Git base ref for flip detection / newness / growth (default origin/dev).",
    )
    parser.add_argument(
        "--node-id",
        default=None,
        help="Verify exactly this node (bypasses PR flip-discovery).",
    )
    args = parser.parse_args(argv)

    s_src, _glob, s_base, s_recv = _apply_scope(
        args.package, args.src_root, args.receipts_dir, args.baseline
    )

    # Parity-debt shrink-only ratchet (OMN-15344). Runs BEFORE flip discovery and
    # independently of it: the population it governs is the ALREADY-MERGED receipts,
    # which by definition produce no flips in this PR.
    parity_baseline_path = _resolve_parity_baseline(s_base, args.parity_baseline)
    try:
        parity_working = load_parity_baseline(parity_baseline_path)
    except ValueError as exc:
        print(f"verify_flip_bundle FAILED (OMN-15344) — {exc}", file=sys.stderr)
        return 1
    parity_base, parity_base_existed = load_base_parity_baseline(
        parity_baseline_path, args.base_ref
    )
    ratchet_errors = _parity_debt_ratchet(
        parity_working,
        parity_base,
        parity_base_existed,
        s_recv,
        chs._git_repo_root(s_src),
        s_src,
        args.base_ref,
    )
    if ratchet_errors:
        print(
            f"verify_flip_bundle FAILED (OMN-15344) — the parity-red-on-base debt "
            f"baseline is SHRINK-ONLY; {len(ratchet_errors)} violation(s):",
            file=sys.stderr,
        )
        for err in ratchet_errors:
            print(f"    - {err}", file=sys.stderr)
        return 1
    if parity_working:
        print(
            f"verify_flip_bundle NOTE — {len(parity_working)} node(s) carry baselined "
            f"parity-red-on-base debt ({parity_baseline_path.name}); shrink-only. Burn "
            f"down by making the declared parity tests assert the def-A -> def-B "
            f"transition, then remove the entry (the gate re-executes assertion 7)."
        )

    if args.node_id:
        node_ids: list[str] | None = [args.node_id]
    else:
        node_ids = _newly_flipped_nodes(s_src, s_base, s_recv, args.base_ref)
        if node_ids is None:
            print(
                "verify_flip_bundle NOTE — git base unavailable; PR flip-discovery "
                "skipped (the canonical_handler_shape ratchet still hard-guards new "
                "non-canonical nodes on this run).",
                file=sys.stderr,
            )
            return 0

    if not node_ids:
        print(
            f"verify_flip_bundle OK ({args.package}) — no canonical-shape flips in this "
            f"PR to prove."
        )
        return 0

    failures = 0
    for node_id in node_ids:
        result = verify_flip_bundle(
            node_id,
            args.package,
            args.src_root,
            args.receipts_dir,
            args.baseline,
            base_ref=args.base_ref,
            parity_baseline=frozenset(parity_working),
        )
        if result.ok:
            tag = " (grandfathered a6)" if result.grandfathered else ""
            print(f"verify_flip_bundle OK — {node_id}{tag}: {result.reason}")
        else:
            failures += 1
            print(
                f"verify_flip_bundle FAIL — {node_id}: {result.reason}", file=sys.stderr
            )
            for outcome in result.outcomes:
                mark = "ok " if outcome.ok else "FAIL"
                print(
                    f"    [{mark}] assertion {outcome.index} {outcome.name}: "
                    f"{outcome.detail}",
                    file=sys.stderr,
                )

    if failures:
        print(
            f"\nverify_flip_bundle FAILED (OMN-14809) — {failures}/{len(node_ids)} "
            f"flip bundle(s) incoherent. A canonical-shape flip must carry five coherent "
            f"artifacts; fix the offending artifact above (do NOT weaken the gate).",
            file=sys.stderr,
        )
        return 1
    print(
        f"verify_flip_bundle OK ({args.package}) — {len(node_ids)} flip bundle(s) "
        f"coherent across all seven assertions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
