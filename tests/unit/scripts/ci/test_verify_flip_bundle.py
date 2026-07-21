# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the fail-closed flip-bundle seam gate (OMN-14809, LANE c).

Proves two things:

1. ``verify_flip_bundle`` PASSES assertions 1-5 (6 grandfathered) on the two committed
   proven flips in omnibase_infra (skipped when the sibling clone is unavailable, e.g.
   omnibase_core CI, where the synthetic positive case carries the pass-path proof).
2. On seeded-incoherent bundles it FAILS on the INTENDED assertion, not incidentally —
   the gate stops at the first failing assertion, so a case that reports
   ``failed_assertion == N`` necessarily passed 1..N-1.

Seeded cases (task-mandated):
  (a) forged adequacy (selected_count != len(selected_input_hashes)) -> assertion 1 (A1)
  (b) multi-handler node with only binding[0] flipped                -> assertion 3 (B5)
  (c) equivalence provenance identity == the def-B author            -> assertion 6 (E1)
  (d) receipt sha mismatches after a dry-run ruff format             -> assertion 5 (S1)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.ci.verify_flip_bundle import ModelFlipBundleResult, verify_flip_bundle

pytestmark = pytest.mark.unit

# Two distinct git identities: X = def-B (handler) author, Y = independent golden author.
AUTHOR_X = ("Def B Author", "defb@example.test")
AUTHOR_Y = ("Independent Reviewer", "reviewer@example.test")

NODE_ID = "testpkg.nodes.node_demo_compute"
PACKAGE = "testpkg"
_DUMMY_INPUT_HASH = "sha256:" + "a" * 64

CANONICAL_HANDLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


class HandlerDemoCompute:
    def handle(self, request):
        return request
"""

# Deliberately un-ruff-formatted (``self,request`` -> ``self, request`` on format), still
# a canonical def-B handle(). Used by seeded case (d).
UNFORMATTED_HANDLER = (
    "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
    "# SPDX-License-Identifier: MIT\n"
    "class HandlerDemoCompute:\n"
    "    def handle(self,request):\n"
    "        return request\n"
)

LEGACY_HANDLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


class HandlerDemoCompute:
    def run(self, payload):
        return payload
"""

NON_CANONICAL_BAD_HANDLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


class HandlerBad:
    def run(self, payload):
        return payload
"""

SINGLE_BINDING_CONTRACT = """name: node_demo_compute
node_type: COMPUTE_GENERIC
handler:
  class: HandlerDemoCompute
  module: testpkg.nodes.node_demo_compute.handler
"""

# Multi-handler: binding[0] canonical (matches the receipt), binding[1] non-canonical.
MULTI_BINDING_CONTRACT = """name: node_demo_compute
node_type: COMPUTE_GENERIC
handler_routing:
  routing_strategy: operation_match
  handlers:
    - operation: good
      handler:
        class: HandlerDemoCompute
        module: testpkg.nodes.node_demo_compute.handler
    - operation: bad
      handler:
        class: HandlerBad
        module: testpkg.nodes.node_demo_compute.handler_bad
"""


def _git(repo: Path, *args: str, author: tuple[str, str] | None = None) -> str:
    env = None
    if author is not None:
        name, email = author
        env = {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
        }
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**_base_env(), **(env or {})},
    )
    return proc.stdout.strip()


def _base_env() -> dict[str, str]:
    # Keep git deterministic + isolated from the developer's global config.
    env = dict(os.environ)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        env.pop(key, None)
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    return env


def test_base_env_does_not_inherit_parent_git_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/parent/worktree/.git")

    assert "GIT_DIR" not in _base_env()


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class FlipRepo:
    root: Path
    src_root: Path
    receipts_dir: Path
    baseline_path: Path
    handler_file: Path
    contract_file: Path
    base_ref: str  # commit1 (Y) — origin/dev pre-flip
    anchor_x: str  # commit0 (X) — an X-authored ancestor
    def_b_commit: str  # commit2 (X) — the flip commit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_flip_repo(tmp_path: Path, *, formatted: bool = True) -> FlipRepo:
    """A real 3-commit git repo carrying one coherent NEW canonical-shape flip.

    Timeline (authors matter for the assertion-6 git-anchored attestation):
      commit0 (X): scaffold + legacy handler + baseline listing the node non-canonical.
      commit1 (Y): trivial anchor commit (origin/dev pre-flip == base_ref).
      commit2 (X): the flip — canonical handler + baseline shrink + adequacy/equivalence.
    """
    root = tmp_path / "repo"
    src_root = root / "src"
    node_dir = src_root / "testpkg" / "nodes" / "node_demo_compute"
    receipts_dir = root / "scripts" / "ci" / "adequacy_receipts"
    baseline_path = root / "scripts" / "ci" / "canonical_handler_shape_baseline.py"
    handler_file = node_dir / "handler.py"
    contract_file = node_dir / "contract.yaml"

    root.mkdir(parents=True)
    _git(root, "init", "-q")

    # commit0 (X): base state, node non-canonical.
    _write(contract_file, SINGLE_BINDING_CONTRACT)
    _write(handler_file, LEGACY_HANDLER)
    _write(baseline_path, 'NON_CANONICAL = ("testpkg.nodes.node_demo_compute",)\n')
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base state (non-canonical)", author=AUTHOR_X)
    anchor_x = _git(root, "rev-parse", "HEAD")

    # commit1 (Y): trivial anchor == the golden's pre-flip re-exec point / origin/dev.
    _write(root / "docs" / "anchor.md", "pre-flip base\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "pre-flip anchor", author=AUTHOR_Y)
    base_ref = _git(root, "rev-parse", "HEAD")

    # commit2 (X): the flip. Canonical handler first (optionally ruff-formatted), THEN
    # hash it, THEN mint the receipt (S1 ordering), THEN shrink the baseline.
    _write(handler_file, CANONICAL_HANDLER if formatted else UNFORMATTED_HANDLER)
    if formatted:
        _ruff_format(handler_file)
    handler_sha = _sha256_file(handler_file)

    receipt = {
        "receipt_schema": "adequacy_receipt.v1",
        "node_id": NODE_ID,
        "handler_module": "testpkg.nodes.node_demo_compute.handler",
        "handler_module_sha256": handler_sha,
        "recorded_at": "2026-07-19T00:00:00+00:00",
        "recorder_schema": "adequacy_receipt.v1",
        "candidate_count": 1,
        "selected_count": 1,
        "selected_input_hashes": [_DUMMY_INPUT_HASH],
        "branch_coverage_pct": 100.0,
        "coverage_target": 80.0,
        "meets_target": True,
        "uncovered_waiver": None,
        "volatile_mask": [],
    }
    _write(receipts_dir / f"{NODE_ID}.json", json.dumps(receipt, indent=2))

    # POSITIVE provenance: golden authored by Y (independent of def-B author X),
    # git-anchored at the Y-authored base_ref, def_b_commit == the flip commit (X).
    def_b_commit_placeholder = "PENDING"  # filled after this commit exists
    equivalence = {
        "node_id": NODE_ID,
        "selected_input_hashes": [_DUMMY_INPUT_HASH],
        "status": "pass",
        "provenance": {
            "authored_by": AUTHOR_Y[1],
            "def_b_commit": def_b_commit_placeholder,
            "base_ref_exec_sha": base_ref,
        },
    }
    equiv_path = receipts_dir / f"{NODE_ID}.equivalence.json"
    _write(equiv_path, json.dumps(equivalence, indent=2))

    _write(baseline_path, "NON_CANONICAL = ()\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "flip to canonical def-B", author=AUTHOR_X)
    def_b_commit = _git(root, "rev-parse", "HEAD")

    # Now that the flip commit exists, fill def_b_commit into the working-tree
    # equivalence artifact (the gate reads working-tree receipts).
    equivalence["provenance"]["def_b_commit"] = def_b_commit
    _write(equiv_path, json.dumps(equivalence, indent=2))

    return FlipRepo(
        root=root,
        src_root=src_root,
        receipts_dir=receipts_dir,
        baseline_path=baseline_path,
        handler_file=handler_file,
        contract_file=contract_file,
        base_ref=base_ref,
        anchor_x=anchor_x,
        def_b_commit=def_b_commit,
    )


def _ruff_format(path: Path) -> None:
    for argv in (
        ["ruff", "format", str(path)],
        ["uv", "run", "ruff", "format", str(path)],
    ):
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        except OSError:
            continue
        if proc.returncode == 0:
            return
    raise RuntimeError("ruff format unavailable in test environment")


def _run(repo: FlipRepo) -> ModelFlipBundleResult:
    return verify_flip_bundle(
        NODE_ID,
        PACKAGE,
        repo.src_root,
        repo.receipts_dir,
        repo.baseline_path,
        base_ref=repo.base_ref,
    )


# --------------------------------------------------------------------------- #
# 1. PASS on a coherent NEW flip (synthetic; runs everywhere incl. core CI).
# --------------------------------------------------------------------------- #


def test_passes_on_coherent_new_flip(tmp_path: Path) -> None:
    repo = build_flip_repo(tmp_path)
    result = _run(repo)
    assert result.ok, result.reason
    assert result.failed_assertion is None
    # Assertion 6 genuinely RAN the independent-author attestation (not grandfathered):
    assert result.grandfathered is False
    a6 = next(o for o in result.outcomes if o.index == 6)
    assert "!=" in a6.detail and "git-anchored" in a6.detail
    # All six assertions recorded ok.
    assert [o.index for o in result.outcomes] == [1, 2, 3, 4, 5, 6]
    assert all(o.ok for o in result.outcomes)


# --------------------------------------------------------------------------- #
# 2. PASS on the two committed proven flips in omnibase_infra (real bundles).
# --------------------------------------------------------------------------- #


def _resolve_infra_root() -> Path | None:
    """Locate the omnibase_infra canonical clone (env-var first, never hardcoded)."""
    candidates: list[Path] = []
    omni_home = os.environ.get("OMNI_HOME")
    if omni_home:
        candidates.append(Path(omni_home) / "omnibase_infra")
    here = Path(__file__).resolve()
    # Walk up looking for a sibling omnibase_infra (canonical workspace layout).
    for parent in here.parents:
        candidates.append(parent / "omnibase_infra")
    for cand in candidates:
        if (cand / "scripts/ci/adequacy_receipts").is_dir():
            return cand
    return None


_INFRA_ROOT = _resolve_infra_root()
_INFRA_FLIPS = [
    "omnibase_infra.nodes.node_coding_agent_invoke_effect",
    "omnibase_infra.nodes.node_coding_agent_workspace_compute",
]


@pytest.mark.skipif(
    _INFRA_ROOT is None,
    reason="omnibase_infra canonical clone not present (e.g. isolated core CI)",
)
@pytest.mark.parametrize("node_id", _INFRA_FLIPS)
def test_passes_on_committed_infra_flips(node_id: str) -> None:
    assert _INFRA_ROOT is not None  # guarded by skipif
    result = verify_flip_bundle(
        node_id,
        "omnibase_infra",
        _INFRA_ROOT / "src",
        _INFRA_ROOT / "scripts/ci/adequacy_receipts",
        _INFRA_ROOT / "scripts/ci/canonical_handler_shape_baseline.py",
        base_ref="origin/dev",
    )
    assert result.ok, result.reason
    # Assertions 1-5 hold; assertion 6 is grandfathered (proof pre-existing at origin/dev).
    assert result.grandfathered is True
    for idx in (1, 2, 3, 4, 5):
        outcome = next(o for o in result.outcomes if o.index == idx)
        assert outcome.ok, f"assertion {idx}: {outcome.detail}"
    # Assertion 4 genuinely exercised the entrypoint twin-baseline (infra HAS that gate).
    a4 = next(o for o in result.outcomes if o.index == 4)
    assert "known_entrypointless" in a4.detail


# --------------------------------------------------------------------------- #
# 3. Seeded-incoherent bundles — each FAILS on its intended assertion.
# --------------------------------------------------------------------------- #


def test_seed_a_forged_adequacy_fails_assertion_1(tmp_path: Path) -> None:
    """selected_count != len(selected_input_hashes) -> ModelAdequacyReceipt invalid."""
    repo = build_flip_repo(tmp_path)
    receipt_path = repo.receipts_dir / f"{NODE_ID}.json"
    raw = json.loads(receipt_path.read_text())
    raw["candidate_count"] = 2
    raw["selected_count"] = 2  # but selected_input_hashes still has length 1
    receipt_path.write_text(json.dumps(raw, indent=2))

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 1, result.reason
    assert "selected_count" in result.reason


def test_seed_b_multi_handler_partial_flip_fails_assertion_3(tmp_path: Path) -> None:
    """binding[0] canonical, binding[1] not — classify_node(bindings[0]) is blind."""
    repo = build_flip_repo(tmp_path)
    # Rewrite the contract to two bindings; add a non-canonical second handler.
    repo.contract_file.write_text(MULTI_BINDING_CONTRACT, encoding="utf-8")
    (repo.handler_file.parent / "handler_bad.py").write_text(
        NON_CANONICAL_BAD_HANDLER, encoding="utf-8"
    )

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 3, result.reason
    assert "handler_bad" in result.reason and "partial flip" in result.reason


def test_seed_c_self_authored_golden_fails_assertion_6(tmp_path: Path) -> None:
    """authored_by == def-B author (git-anchored to an X-authored ancestor) -> E1 FAIL."""
    repo = build_flip_repo(tmp_path)
    equiv_path = repo.receipts_dir / f"{NODE_ID}.equivalence.json"
    raw = json.loads(equiv_path.read_text())
    # Golden claims to be authored by X (the def-B author), git-anchored at the
    # X-authored ancestor (so the git-anchor check passes and the failure is the
    # identity match, not an incidental unresolvable/anchor failure).
    raw["provenance"]["authored_by"] = AUTHOR_X[1]
    raw["provenance"]["base_ref_exec_sha"] = repo.anchor_x
    equiv_path.write_text(json.dumps(raw, indent=2))

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 6, result.reason
    assert "self-authored by the def-B author" in result.reason


def test_seed_d_receipt_minted_pre_format_fails_assertion_5(tmp_path: Path) -> None:
    """Handler is not ruff-formatted; receipt sha matches the un-formatted file.

    5a (live sha == recorded) holds, but a dry-run ruff format WOULD change the file,
    so the receipt was minted before the final format -> 5b FAILS.
    """
    repo = build_flip_repo(tmp_path, formatted=False)
    # Sanity: assertion 2's live-sha check still passes (recorded == unformatted live).
    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 5, result.reason
    assert "PRE-format" in result.reason


# --------------------------------------------------------------------------- #
# 4. Guardrail: assertion 6 fails CLOSED when the provenance block is entirely absent.
# --------------------------------------------------------------------------- #


def test_new_equivalence_flip_without_provenance_fails_assertion_6(
    tmp_path: Path,
) -> None:
    repo = build_flip_repo(tmp_path)
    equiv_path = repo.receipts_dir / f"{NODE_ID}.equivalence.json"
    raw = json.loads(equiv_path.read_text())
    raw.pop("provenance", None)
    equiv_path.write_text(json.dumps(raw, indent=2))

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 6, result.reason
    assert "missing provenance block" in result.reason


def test_missing_adequacy_receipt_fails_closed_assertion_1(tmp_path: Path) -> None:
    repo = build_flip_repo(tmp_path)
    (repo.receipts_dir / f"{NODE_ID}.json").unlink()
    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 1
    assert "absent" in result.reason
