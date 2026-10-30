# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-derive no-legacy and already-landed flip proofs from Git history."""

from __future__ import annotations

import ast
import os
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_flip_artifacts import (
    EXPECTED_NO_LEGACY_SCHEMA,
    LEGACY_HANDLER_NONE,
    _display_path,
    _load_json,
    _module_repo_rel,
    _resolve_module_file,
    _sha256_file,
)
from omnibase_core.validation.validator_flip_binding import (
    _classes,
    _contract_bindings,
    load_binding_document,
)
from omnibase_core.validation.validator_flip_git import (
    _git_is_ancestor,
    _git_lines,
    _git_ls_tree,
    _git_merge_base,
    _git_no_diff,
    _git_ref_exists,
    _git_repo_root,
    _git_show,
)
from omnibase_core.validation.validator_flip_parity import (
    ParityExecutor,
    default_parity_executor,
)
from omnibase_core.validation.validator_flip_scope import SCOPE


def _landed_no_legacy_flip(
    repo_root: Path, live_base: str, base_ref: str, node_id: str, receipt_path: Path
) -> tuple[bool, str]:
    """Whether the live merge base already carries this exact no-legacy flip.

    After a no-legacy flip merges, the live merge base holds the flip's own new
    handler, so the live-base check refuses the receipt on every later run until
    the baseline drops the node, and the change that drops it is refused for the
    same reason. The flip is accepted as landed only when every claim is
    re-derived from git:
      * the receipt was added by a commit ``L`` on the live merge base's history;
      * the node directory and the receipt are unchanged from ``L`` through the
        live merge base to the working tree, with no untracked file in the node
        directory (this run changes nothing the landed flip did not);
      * ``base_ref`` is an ancestor of ``L``, and every commit from ``base_ref``
        to ``L`` that changed the node either had no handler or already held the
        node exactly as ``L`` landed it (the flip's own handler commit).
    A different handler that existed on the base before the receipt landed is
    still refused, and so is any change to the node made after it landed.
    """
    src_rel = _src_rel(repo_root)
    if src_rel is None:
        return False, "SCOPE.src_root is outside the git repo"
    try:
        receipt_rel = str(
            receipt_path.resolve().relative_to(repo_root.resolve())
        ).replace(os.sep, "/")
    except ValueError:
        return False, "receipt is outside the git repo"
    node_rel = "/".join(p for p in (src_rel, node_id.replace(".", "/")) if p)

    added = _git_lines(
        repo_root,
        "log",
        "-n1",
        "--diff-filter=A",
        "--format=%H",
        live_base,
        "--",
        receipt_rel,
    )
    if not added:
        return False, "the receipt did not land on the live merge base"
    landed = added[0]
    if not _git_no_diff(repo_root, landed, live_base, "--", node_rel, receipt_rel):
        return False, f"node or receipt changed between {landed[:12]} and the base"
    if not _git_no_diff(repo_root, landed, "--", node_rel, receipt_rel):
        return False, f"node or receipt changed since {landed[:12]} landed"
    untracked = _git_lines(
        repo_root, "ls-files", "--others", "--exclude-standard", "--", node_rel
    )
    if untracked is None or untracked:
        return False, "untracked files in the node directory"
    if not _git_is_ancestor(repo_root, base_ref, landed):
        return False, f"receipt base_ref is not an ancestor of {landed[:12]}"
    landed_tree = _git_lines(repo_root, "rev-parse", f"{landed}:{node_rel}")
    touching = _git_lines(
        repo_root, "rev-list", "--full-history", f"{base_ref}..{landed}", "--", node_rel
    )
    if landed_tree is None or touching is None:
        return False, f"cannot read the node history from base_ref to {landed[:12]}"
    for commit in touching:
        _, evidence = _legacy_handler_evidence(repo_root, commit, node_id)
        if evidence is None:
            continue
        if _git_lines(repo_root, "rev-parse", f"{commit}:{node_rel}") != landed_tree:
            return False, f"before the receipt landed: {evidence}"
    return True, f"flip landed at {landed[:12]} with no other handler before it"


def _src_rel(repo_root: Path) -> str | None:
    """``SCOPE.src_root`` relative to ``repo_root`` (posix), or None if outside it."""
    try:
        rel = SCOPE.src_root.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    rel_str = str(rel).replace(os.sep, "/")
    return "" if rel_str == "." else rel_str


def _module_rel_candidates(src_rel: str, module: str) -> list[str]:
    stem = module.replace(".", "/")
    prefix = f"{src_rel}/" if src_rel else ""
    return [f"{prefix}{stem}.py", f"{prefix}{stem}/__init__.py"]


def _legacy_handler_evidence(
    repo_root: Path, ref: str, node_id: str
) -> tuple[list[str] | None, str | None]:
    """``(node_files_at_ref, handler_evidence)`` for a node as it was at ``ref``.

    ``handler_evidence`` is None when NO handler existed at ``ref``; otherwise it
    names what the gate found. Fail-closed: anything handler-shaped counts, i.e.
      * a contract binding whose module file existed at ``ref``, or an empty-module
        binding whose class was defined in the node package at ``ref``;
      * a node file named ``handler*.py`` or under a ``handlers/`` directory;
      * a node module defining a ``Handler*`` class or a class with ``handle`` /
        ``handle_async``.
    ``node_files_at_ref`` is None when the listing itself is unreadable.
    """
    src_rel = _src_rel(repo_root)
    if src_rel is None:
        return (
            None,
            "SCOPE.src_root is outside the git repo; cannot read the node at ref",
        )
    node_rel = "/".join(p for p in (src_rel, node_id.replace(".", "/")) if p)
    files = _git_ls_tree(repo_root, ref, node_rel)
    if files is None:
        return None, f"git ls-tree failed for {ref}:{node_rel}"
    if not files:
        return files, f"node directory {node_rel} absent at {ref}"

    node_classes: set[str] = set()
    for rel in files:
        tail = rel[len(node_rel) + 1 :]
        name = tail.rsplit("/", 1)[-1]
        if "/handlers/" in f"/{tail}" or (
            name.startswith("handler") and name.endswith(".py")
        ):
            return files, f"handler file {rel} existed at {ref}"
        if not rel.endswith(".py"):
            continue
        text = _git_show(repo_root, ref, rel)
        if text is None:
            return files, f"cannot read {ref}:{rel}"
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return files, f"{ref}:{rel} unparseable; cannot rule out a handler"
        for c in _classes(tree):
            node_classes.add(c.name)
            if c.name.startswith("Handler"):
                return files, f"class {c.name} in {rel} at {ref}"
            for m in c.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    m.name in ("handle", "handle_async")
                ):
                    return files, f"{c.name}.{m.name} in {rel} at {ref}"

    contract_src = _git_show(repo_root, ref, f"{node_rel}/contract.yaml")
    if contract_src is not None:
        try:
            data = load_binding_document(contract_src)
        except ModelOnexError:
            return files, f"contract.yaml unparseable at {ref}"
        if isinstance(data, dict):
            for module, cls in _contract_bindings(data):
                if not module:
                    if cls in node_classes:
                        return files, (
                            f"contract bound in-package class {cls!r}, defined at {ref}"
                        )
                    continue
                for cand in _module_rel_candidates(src_rel, module):
                    if _git_show(repo_root, ref, cand) is not None:
                        return files, (
                            f"contract bound handler module {module} and {cand} "
                            f"existed at {ref}"
                        )
    return files, None


def verify_no_legacy_flip(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str]:
    """Proof for a flip of a node that had NO legacy handler (OMN-20298).

    The adequacy receipt carries ``legacy_handler: "none"``. Every claim in it is
    re-derived, never trusted:
      * ``base_ref`` resolves and is an ancestor of HEAD;
      * ``base_node_files`` equals ``git ls-tree`` of the node directory at
        ``base_ref`` (the evidence is the listing at that commit);
      * no handler existed at ``base_ref`` NOR at the live merge base of HEAD with
        ``SCOPE.base_ref`` (so an older handler-less commit cannot be cited past a handler
        that exists on the base today), unless that handler is this flip's own,
        already landed with no handler before it (``_landed_no_legacy_flip``);
      * the new handler module's sha256 is fresh;
      * every declared ``contract_tests`` file names the node package, and the ids
        are EXECUTED green on HEAD (a recorded status is not evidence).
    """
    receipt_path = SCOPE.receipts_dir / f"{node_id}.json"
    raw = _load_json(receipt_path)
    if raw is None:
        return False, f"no-legacy receipt unreadable at {_display_path(receipt_path)}"
    if raw.get("node_id") != node_id:
        return False, f"receipt node_id {raw.get('node_id')!r} != {node_id!r}"
    if raw.get("legacy_handler") != LEGACY_HANDLER_NONE:
        return False, (
            f"legacy_handler={raw.get('legacy_handler')!r}; only 'none' is a "
            f"no-legacy receipt — a node with a legacy handler needs the "
            f"equivalence-replay or hand-flip proof"
        )
    if raw.get("receipt_schema") != EXPECTED_NO_LEGACY_SCHEMA:
        return (
            False,
            f"unexpected no-legacy receipt_schema {raw.get('receipt_schema')!r}",
        )

    module = raw.get("handler_module") or handler_module
    if not isinstance(module, str) or not module:
        return False, "no-legacy receipt has no handler_module"
    module_file = _resolve_module_file(module)
    if module_file is None:
        return False, f"handler_module {module} not resolvable for freshness check"
    if _sha256_file(module_file) != raw.get("handler_module_sha256"):
        return False, "stale receipt: live handler_module_sha256 != recorded"

    base_ref = raw.get("base_ref")
    if not isinstance(base_ref, str) or not base_ref:
        return False, "no-legacy receipt missing base_ref"
    repo_root = _git_repo_root(SCOPE.src_root)
    if repo_root is None:
        return False, f"cannot resolve a git repo root from {SCOPE.src_root}"
    if not _git_ref_exists(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} unresolvable"
    if not _git_is_ancestor(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} is not an ancestor of HEAD"

    files, evidence = _legacy_handler_evidence(repo_root, base_ref, node_id)
    if evidence is not None:
        return False, f"legacy handler existed: {evidence}"
    recorded = raw.get("base_node_files")
    if not isinstance(recorded, list) or sorted(str(f) for f in recorded) != files:
        return False, (
            f"base_node_files does not match git ls-tree at {base_ref}: "
            f"recorded={recorded!r} actual={files!r}"
        )
    live_base = (
        _git_merge_base(repo_root, SCOPE.base_ref)
        if _git_ref_exists(repo_root, SCOPE.base_ref)
        else None
    )
    if live_base is not None and live_base != base_ref:
        _, live_evidence = _legacy_handler_evidence(repo_root, live_base, node_id)
        if live_evidence is not None:
            landed, landed_reason = _landed_no_legacy_flip(
                repo_root, live_base, base_ref, node_id, receipt_path
            )
            if not landed:
                return (
                    False,
                    f"legacy handler existed at the live merge base: {live_evidence} "
                    f"(not a landed no-legacy flip: {landed_reason})",
                )
            # A no-legacy flip introduces a handler. Once it lands, the live
            # merge base necessarily has that handler, so descendants must be
            # able to retain the original proof. Only accept the identical
            # receipt AND handler already on the trusted base; an older
            # handlerless commit still cannot justify replacing a live handler.
            module_rel = _module_repo_rel(module)
            try:
                receipt_rel = receipt_path.resolve().relative_to(repo_root.resolve())
            except ValueError:
                receipt_rel = None
            already_landed = (
                receipt_rel is not None
                and module_rel is not None
                and _git_is_ancestor(repo_root, base_ref, live_base)
                and _git_show(repo_root, live_base, receipt_rel.as_posix())
                == receipt_path.read_text(encoding="utf-8")
                and _git_show(repo_root, live_base, module_rel[1])
                == module_file.read_text(encoding="utf-8")
            )
            if not already_landed:
                return (
                    False,
                    f"legacy handler existed at the live merge base: {live_evidence}",
                )

    tests_raw = raw.get("contract_tests")
    test_ids = tuple(str(t) for t in tests_raw) if isinstance(tests_raw, list) else ()
    if not test_ids:
        return False, "no-legacy receipt names no contract_tests"
    for test_file in sorted({t.split("::", 1)[0] for t in test_ids}):
        path = repo_root / test_file
        if not path.is_file():
            return False, f"contract test file {test_file} absent"
        if node_id not in path.read_text(encoding="utf-8"):
            return False, f"contract test file {test_file} never names {node_id}"
    executor = (
        parity_executor if parity_executor is not None else default_parity_executor
    )
    verdict = executor(node_id, test_ids)
    if not verdict.executed:
        return False, f"contract tests UNEXECUTED ({verdict.detail})"
    if not verdict.green:
        return False, f"contract tests NOT GREEN when executed: {verdict.detail}"
    return True, (
        f"no-legacy-handler-at-{base_ref[:12]}"
        f"+contract-tests-executed-green({len(test_ids)} test id(s))"
    )
