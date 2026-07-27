# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic producer + byte-compare comparator for equivalence artifacts (OMN-14905).

``canonical_handler_shape.verify_equivalence_replay`` TRUSTS ``status == "pass"`` and
never re-runs the replay it gates (blind spot E1). The first attempt to close E1
(omnibase_core#1472, ``verify_flip_bundle._assert_independent_author``) asserted an
**author identity** property — ``authored_by != git-author(def_b_commit)``. Identity is
not evidence: any second git identity (a bot, a second machine, a co-authored trailer)
satisfies that assertion while proving exactly nothing about the artifact.

This module replaces identity with **mechanical reproducibility**, the OMN-14393 pattern
(``verify_companion_attestation``: recompute the plan, byte-diff the deterministic
fingerprint):

1. The artifact carries a ``declaration`` — the *inputs* to the replay (which legacy
   module at which pre-flip commit, which canonical entry-point, which replay input
   files, which volatile mask). A declaration names inputs; it never asserts a verdict.
2. :func:`produce` RE-EXECUTES the replay from ground truth — the HEAD canonical handler
   against the legacy handler materialized straight out of ``git show <base_ref>:<path>``
   — and DERIVES the two verdict fields (``selected_input_hashes``, ``status``).
3. :func:`byte_compare` re-emits the whole artifact canonically and compares it
   **byte-for-byte** against what the PR carries.

Identical bytes prove the artifact is mechanically reproducible. A forged ``status``, a
fabricated input hash, or a golden that no longer matches live code all diverge on the
byte-compare. Who typed the file is irrelevant, which is the point.

Why the legacy side cannot be fabricated: it is read from git, never from a committed
golden. This mirrors ``canonical_handler_shape.verify_handflip_proof``, which already
git-re-derives its verbatim-preservation proof — and which is exactly why the hand-flip
path was already exempt from the identity assertion.

Two narrowing attacks are closed elsewhere and are deliberately NOT re-implemented here:

* **Input-set narrowing** (declare fewer/easier replay inputs, derive a consistent
  smaller hash set). ``verify_flip_receipt`` requires
  ``set(adequacy.selected_input_hashes) == set(proof.selected_input_hashes)``, and the
  adequacy verdict is itself re-derived from raw coverage numbers.
* **Legacy-side collapse** (point ``base_ref`` at the flip commit itself so "legacy" IS
  the canonical code and the replay passes trivially). :func:`produce` requires
  ``declaration.base_ref`` to be an ancestor of (or equal to) the gate's base ref, so the
  legacy side is always genuinely pre-PR code.

Fail-closed everywhere: an unreadable artifact, a missing declaration key, an
unresolvable ref, an unimportable module, or ANY exception raised during replay yields
``(None, reason)`` -> the comparator FAILS. There is no "could not verify -> pass" path.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

# Canonical schema tag for a reproducible (v2) equivalence artifact. v1 artifacts (bare
# ``{node_id, selected_input_hashes, status}``) carry no declaration and therefore cannot
# be reproduced; they are only reachable via the grandfathering path in the caller.
EQUIVALENCE_SCHEMA_V2 = "equivalence_replay.v2"

# Every key a v2 declaration must carry. Exact-set (not superset): an unknown key means
# the artifact was written against a different producer than the one verifying it.
REQUIRED_DECLARATION_KEYS: frozenset[str] = frozenset(
    {
        "base_ref",
        "legacy_handler_module",
        "legacy_handler_symbol",
        "legacy_entrypoint",
        "canonical_handler_module",
        "canonical_handler_symbol",
        "canonical_entrypoint",
        "input_model",
        "replay_inputs",
        "volatile_mask",
    }
)


def canonical_bytes(artifact: dict[str, Any]) -> bytes:
    """The one canonical on-disk encoding of an equivalence artifact.

    Sorted keys + 2-space indent + trailing newline. Producer and committed file MUST
    agree on this exact encoding, otherwise the byte-compare would report cosmetic
    formatting drift as tampering.
    """
    return (
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _git(repo_root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent
        return 1, str(exc)
    return proc.returncode, proc.stdout


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@contextlib.contextmanager
def _src_root_first(src_root: Path) -> Iterator[None]:
    """Put ``src_root`` at the FRONT of ``sys.path`` for the duration of the replay.

    The gate must execute the module in the WORKING TREE — the same file whose sha
    assertion 5 pinned to the adequacy receipt — not whatever copy happens to be
    installed in site-packages. (It also makes the synthetic fan-out/test packages
    importable at all.)
    """
    entry = str(src_root.resolve())
    preexisting = frozenset(sys.modules)
    sys.path.insert(0, entry)
    try:
        yield
    finally:
        try:
            sys.path.remove(entry)
        except ValueError:  # pragma: no cover - someone else already removed it
            pass
        # Drop modules this replay newly imported FROM src_root, so a second replay
        # against a different tree (fan-out, or the next test case) cannot silently
        # execute the first tree's cached modules. Modules imported before the block are
        # left alone — tearing those down mid-process would hand the rest of the run
        # duplicate class objects.
        #
        # Membership is decided by ``__file__`` ONLY, then generalized to the whole
        # top-level package: a top-level package is "under entry" if ANY newly-imported
        # module in it is a real file under entry. Namespace-package parents (which have
        # no ``__file__``) are then popped by NAME. This deliberately never reads
        # ``__path__`` — doing so lazily recomputes a namespace path against a parent that
        # may already be gone, raising KeyError.
        entry_path = Path(entry).resolve()
        newly = [n for n in sys.modules if n not in preexisting]
        roots_under_entry: set[str] = set()
        for name in newly:
            file = getattr(sys.modules.get(name), "__file__", None)
            if not isinstance(file, str):
                continue
            try:
                Path(file).resolve().relative_to(entry_path)
            except ValueError:
                continue
            roots_under_entry.add(name.split(".", 1)[0])
        for name in newly:
            if name.split(".", 1)[0] in roots_under_entry:
                sys.modules.pop(name, None)


def _import_head_symbol(module: str, symbol: str, src_root: Path) -> tuple[Any, str]:
    """Import ``symbol`` from the LIVE working-tree ``module`` under ``src_root``."""
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # fail-closed: any import failure is a FAIL
        return None, f"cannot import HEAD module {module!r}: {exc}"
    # Fail closed on working-tree/installed drift: executing an installed copy would
    # prove the reproducibility of a file that is not the one under review.
    loaded = getattr(mod, "__file__", None)
    if loaded is not None:
        try:
            Path(loaded).resolve().relative_to(src_root.resolve())
        except ValueError:
            return (
                None,
                f"module {module!r} resolved to {loaded} which is OUTSIDE the "
                f"src-root under review ({src_root}) — refusing to replay an "
                f"installed copy",
            )
    obj = getattr(mod, symbol, None)
    if obj is None:
        return None, f"HEAD module {module!r} has no symbol {symbol!r}"
    return obj, ""


def _import_legacy_symbol(
    repo_root: Path, base_ref: str, module: str, symbol: str
) -> tuple[Any, str]:
    """Import ``symbol`` from ``module`` as it existed at ``base_ref``, read from git.

    The source is materialized from ``git show`` into a temp file and imported under a
    synthetic module name so it cannot collide with (or be shadowed by) the live HEAD
    module of the same dotted path. The legacy module's own imports still resolve against
    the installed HEAD package — a documented, deliberate impurity: the replay isolates
    the HANDLER under test, not the whole dependency closure.
    """
    rel = module.replace(".", "/") + ".py"
    for prefix in ("src/", ""):
        code, source = _git(repo_root, "show", f"{base_ref}:{prefix}{rel}")
        if code == 0:
            break
    else:  # pragma: no cover - unreachable; the loop always binds
        return None, f"legacy module {module!r} unreadable at {base_ref!r}"
    if code != 0:
        return None, f"legacy module {module!r} absent at {base_ref}:{rel}"

    synthetic = f"_onex_legacy_replay_{hashlib.sha256(f'{base_ref}:{rel}'.encode()).hexdigest()[:16]}"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{synthetic}.py"
        path.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location(synthetic, path)
        if spec is None or spec.loader is None:
            return None, f"cannot build import spec for legacy {module!r}"
        legacy_mod: ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[synthetic] = legacy_mod
        try:
            spec.loader.exec_module(legacy_mod)
        except Exception as exc:  # fail-closed
            return None, f"legacy module {module!r} failed to exec at {base_ref}: {exc}"
        finally:
            sys.modules.pop(synthetic, None)
    obj = getattr(legacy_mod, symbol, None)
    if obj is None:
        return None, f"legacy module {module!r}@{base_ref} has no symbol {symbol!r}"
    return obj, ""


def _mask_and_canonicalize(payload: Any, volatile_mask: list[str]) -> str:
    """Structural canonical form of a model dump with volatile paths removed."""
    try:  # pragma: no cover - import shim (mirrors verify_flip_bundle's dual import)
        from scripts.ci.compute_golden import apply_mask
    except ImportError:  # pragma: no cover
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from compute_golden import apply_mask  # type: ignore[import-not-found,no-redef]

    return json.dumps(apply_mask(payload, volatile_mask), sort_keys=True)


def _read_declaration(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    decl = raw.get("declaration")
    if not isinstance(decl, dict):
        return None, "artifact carries no declaration block (not reproducible)"
    keys = set(decl)
    missing = sorted(REQUIRED_DECLARATION_KEYS - keys)
    unknown = sorted(keys - REQUIRED_DECLARATION_KEYS)
    if missing:
        return None, f"declaration missing key(s): {missing}"
    if unknown:
        return None, f"declaration carries unknown key(s): {unknown}"
    if not isinstance(decl.get("replay_inputs"), list) or not decl["replay_inputs"]:
        return None, "declaration.replay_inputs must be a non-empty list"
    if not isinstance(decl.get("volatile_mask"), list):
        return None, "declaration.volatile_mask must be a list"
    for key in REQUIRED_DECLARATION_KEYS - {"replay_inputs", "volatile_mask"}:
        val = decl.get(key)
        if not isinstance(val, str) or not val.strip():
            return None, f"declaration.{key} must be a non-empty string"
    return decl, ""


def produce(
    node_id: str,
    artifact_path: Path,
    repo_root: Path,
    src_root: Path,
    gate_base_ref: str,
) -> tuple[bytes | None, str]:
    """Re-derive the equivalence artifact for ``node_id`` by RERUNNING the replay.

    Reads ONLY the ``declaration`` (the replay inputs) out of the committed artifact and
    derives every verdict field itself. Returns ``(canonical_bytes, detail)`` or
    ``(None, reason)`` on any failure — never a partial or optimistic result.
    """
    try:
        raw = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"equivalence artifact unreadable: {exc}"
    if not isinstance(raw, dict):
        return None, "equivalence artifact is not a JSON object"
    if raw.get("node_id") != node_id:
        return None, "equivalence artifact node_id mismatch"
    if raw.get("receipt_schema") != EQUIVALENCE_SCHEMA_V2:
        return (
            None,
            f"equivalence artifact receipt_schema={raw.get('receipt_schema')!r}; "
            f"a reproducible flip proof must be {EQUIVALENCE_SCHEMA_V2!r}",
        )

    decl, reason = _read_declaration(raw)
    if decl is None:
        return None, reason

    base_ref = str(decl["base_ref"])
    code, _ = _git(
        repo_root, "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"
    )
    if code != 0:
        return None, f"declaration.base_ref {base_ref!r} unresolvable in git"
    # Legacy-side collapse guard: the legacy handler must be genuinely PRE-PR code.
    code, _ = _git(repo_root, "merge-base", "--is-ancestor", base_ref, gate_base_ref)
    if code != 0:
        return (
            None,
            f"declaration.base_ref {base_ref!r} is not an ancestor of the gate base ref "
            f"{gate_base_ref!r} — the 'legacy' side would not be pre-flip code",
        )

    # --- derived field 1: input hashes over the REAL bytes of the declared inputs ----
    input_payloads: list[Any] = []
    selected_input_hashes: list[str] = []
    for rel in decl["replay_inputs"]:
        if not isinstance(rel, str) or not rel.strip():
            return None, "declaration.replay_inputs contains a non-path entry"
        path = repo_root / rel
        try:
            payload_bytes = path.read_bytes()
        except OSError as exc:
            return None, f"replay input {rel} unreadable: {exc}"
        selected_input_hashes.append(_sha256_bytes(payload_bytes))
        try:
            input_payloads.append(json.loads(payload_bytes.decode("utf-8")))
        except (ValueError, UnicodeDecodeError) as exc:
            return None, f"replay input {rel} is not valid JSON: {exc}"

    # --- resolve the three symbols (input model, HEAD handler, git-legacy handler) ---
    model_module, _, model_symbol = str(decl["input_model"]).rpartition(".")
    if not model_module or not model_symbol:
        return None, "declaration.input_model must be a dotted path Module.Class"

    mask = [str(m) for m in decl["volatile_mask"]]
    head_entry = str(decl["canonical_entrypoint"])
    legacy_entry = str(decl["legacy_entrypoint"])
    status = "pass"
    divergences: list[str] = []

    with _src_root_first(src_root):
        input_model, reason = _import_head_symbol(model_module, model_symbol, src_root)
        if input_model is None:
            return None, reason
        head_cls, reason = _import_head_symbol(
            str(decl["canonical_handler_module"]),
            str(decl["canonical_handler_symbol"]),
            src_root,
        )
        if head_cls is None:
            return None, reason
        legacy_cls, reason = _import_legacy_symbol(
            repo_root,
            base_ref,
            str(decl["legacy_handler_module"]),
            str(decl["legacy_handler_symbol"]),
        )
        if legacy_cls is None:
            return None, reason

        # --- derived field 2: status, from an ACTUAL regen-vs-legacy execution ------
        for rel, payload in zip(decl["replay_inputs"], input_payloads, strict=True):
            try:
                request = input_model.model_validate(payload)
            except Exception as exc:
                return (
                    None,
                    f"replay input {rel} does not validate as {model_symbol}: {exc}",
                )
            try:
                head_out = getattr(head_cls(), head_entry)(request)
                legacy_out = getattr(legacy_cls(), legacy_entry)(request)
            except Exception as exc:
                return (
                    None,
                    f"replay execution failed on {rel}: {type(exc).__name__}: {exc}",
                )
            try:
                head_canon = _mask_and_canonicalize(
                    head_out.model_dump(mode="json"), mask
                )
                legacy_canon = _mask_and_canonicalize(
                    legacy_out.model_dump(mode="json"), mask
                )
            except Exception as exc:
                return None, f"replay output not serializable on {rel}: {exc}"
            if head_canon != legacy_canon:
                status = "fail"
                divergences.append(rel)

    produced = {
        "node_id": node_id,
        "receipt_schema": EQUIVALENCE_SCHEMA_V2,
        "declaration": decl,
        "selected_input_hashes": selected_input_hashes,
        "status": status,
    }
    detail = (
        f"replayed {len(input_payloads)} input(s) HEAD.{head_entry} vs "
        f"{base_ref[:8]}.{legacy_entry} -> status={status}"
    )
    if divergences:
        detail += f"; diverged on {divergences}"
    return canonical_bytes(produced), detail


def byte_compare(
    node_id: str,
    artifact_path: Path,
    repo_root: Path,
    src_root: Path,
    gate_base_ref: str,
) -> tuple[bool, str]:
    """Rerun the producer and byte-compare its output against the committed artifact.

    This is the assertion-6 oracle. It replaces author identity entirely: a faithful
    artifact reproduces byte-for-byte regardless of who authored it, and a tampered one
    diverges regardless of whose name is on it.
    """
    produced, detail = produce(
        node_id, artifact_path, repo_root, src_root, gate_base_ref
    )
    if produced is None:
        return False, f"producer could not reproduce the artifact: {detail}"
    try:
        committed = artifact_path.read_bytes()
    except OSError as exc:
        return False, f"committed equivalence artifact unreadable: {exc}"
    if produced == committed:
        return True, f"byte-identical to deterministic producer rerun ({detail})"

    try:
        produced_obj = json.loads(produced.decode("utf-8"))
        committed_obj = json.loads(committed.decode("utf-8"))
    except ValueError:
        return False, f"byte-compare FAILED ({detail}); committed bytes are not JSON"
    diffs = [
        f"{key}: committed={committed_obj.get(key)!r} produced={produced_obj.get(key)!r}"
        for key in ("status", "selected_input_hashes")
        if committed_obj.get(key) != produced_obj.get(key)
    ]
    if not diffs:
        diffs = ["encoding/field drift outside status+selected_input_hashes"]
    return (
        False,
        "byte-compare FAILED — the committed equivalence artifact is NOT what a "
        f"deterministic producer rerun emits ({detail}); {'; '.join(diffs)}",
    )


__all__ = [
    "EQUIVALENCE_SCHEMA_V2",
    "REQUIRED_DECLARATION_KEYS",
    "byte_compare",
    "canonical_bytes",
    "produce",
]
