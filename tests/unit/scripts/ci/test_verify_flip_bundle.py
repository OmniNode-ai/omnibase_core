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
  (c) forged status=pass over a genuinely diverging replay           -> assertion 6 (E1)
  (d) receipt sha mismatches after a dry-run ruff format             -> assertion 5 (S1)

Assertion 6 (OMN-14905) no longer checks author identity. It RERUNS a deterministic
producer over the artifact's declared replay inputs — executing the working-tree
canonical handler against the legacy handler materialized from ``git show`` — and
byte-compares the reproduced artifact against the committed one. So the seeds below
exercise reproducibility, not who signed the file.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.ci import equivalence_producer as eqp
from scripts.ci.verify_flip_bundle import ModelFlipBundleResult, verify_flip_bundle

pytestmark = pytest.mark.unit

# Two distinct git identities kept only so the synthetic history is realistic; assertion
# 6 no longer reads author identity at all.
AUTHOR_X = ("Def B Author", "defb@example.test")
AUTHOR_Y = ("Independent Reviewer", "reviewer@example.test")

NODE_ID = "testpkg.nodes.node_demo_compute"
PACKAGE = "testpkg"
_DUMMY_INPUT_HASH = "sha256:" + "a" * 64

# Self-contained pydantic input model committed INTO the synthetic repo so the producer
# imports everything from the tree under review (no omnibase_core dependency in the
# replay, and the working-tree-vs-installed drift guard has a real src-root to check).
DEMO_MODEL = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelDemoInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: int = 0
    label: str = "x"
"""

INPUT_MODEL_DOTTED = "testpkg.nodes.node_demo_compute.model.ModelDemoInput"
REPLAY_INPUT_REL = (
    "scripts/ci/equivalence_inputs/testpkg.nodes.node_demo_compute/case.json"
)
REPLAY_INPUT_PAYLOAD = {"value": 3, "label": "demo"}

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

# Legacy def-A whose ``run`` returns the payload UNCHANGED -> equivalent to HEAD.handle,
# so the honest replay is status=pass and byte-reproducible.
LEGACY_HANDLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


class HandlerDemoCompute:
    def run(self, payload):
        return payload
"""

# Legacy def-A that GENUINELY diverges from HEAD (mutates a field). The honest replay is
# status=fail; a golden that forges status=pass is the E1 attack assertion 6 must reject.
DIVERGING_LEGACY_HANDLER = """# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT


class HandlerDemoCompute:
    def run(self, payload):
        return payload.model_copy(update={"value": payload.value + 1})
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
    for key in tuple(env):
        if key.startswith("GIT_CONFIG"):
            env.pop(key, None)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        env.pop(key, None)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
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


def _adequacy_receipt(handler_sha: str, input_hashes: list[str]) -> dict[str, object]:
    return {
        "receipt_schema": "adequacy_receipt.v1",
        "node_id": NODE_ID,
        "handler_module": "testpkg.nodes.node_demo_compute.handler",
        "handler_module_sha256": handler_sha,
        "recorded_at": "2026-07-19T00:00:00+00:00",
        "recorder_schema": "adequacy_receipt.v1",
        "candidate_count": len(input_hashes),
        "selected_count": len(input_hashes),
        "selected_input_hashes": input_hashes,
        "branch_coverage_pct": 100.0,
        "coverage_target": 80.0,
        "meets_target": True,
        "uncovered_waiver": None,
        "volatile_mask": [],
    }


def _v2_declaration(base_ref: str) -> dict[str, object]:
    return {
        "base_ref": base_ref,
        "legacy_handler_module": "testpkg.nodes.node_demo_compute.handler",
        "legacy_handler_symbol": "HandlerDemoCompute",
        "legacy_entrypoint": "run",
        "canonical_handler_module": "testpkg.nodes.node_demo_compute.handler",
        "canonical_handler_symbol": "HandlerDemoCompute",
        "canonical_entrypoint": "handle",
        "input_model": INPUT_MODEL_DOTTED,
        "replay_inputs": [REPLAY_INPUT_REL],
        "volatile_mask": [],
    }


def build_flip_repo(
    tmp_path: Path, *, formatted: bool = True, diverging_legacy: bool = False
) -> FlipRepo:
    """A real 3-commit git repo carrying one coherent NEW canonical-shape flip.

    Timeline:
      commit0: scaffold + legacy handler + demo model + baseline (node non-canonical).
      commit1: trivial anchor commit (origin/dev pre-flip == base_ref).
      commit2: the flip — canonical handler + baseline shrink + adequacy + v2 equivalence.

    The v2 equivalence artifact carries a ``declaration`` of the replay inputs only; its
    ``selected_input_hashes`` and ``status`` are DERIVED by rerunning the producer, so a
    faithful fixture is byte-reproducible by construction. ``diverging_legacy`` seeds a
    legacy handler that genuinely diverges from HEAD (honest status=fail) for the E1
    attack case.
    """
    root = tmp_path / "repo"
    src_root = root / "src"
    node_dir = src_root / "testpkg" / "nodes" / "node_demo_compute"
    receipts_dir = root / "scripts" / "ci" / "adequacy_receipts"
    baseline_path = root / "scripts" / "ci" / "canonical_handler_shape_baseline.py"
    handler_file = node_dir / "handler.py"
    contract_file = node_dir / "contract.yaml"
    model_file = node_dir / "model.py"
    input_file = root / REPLAY_INPUT_REL

    root.mkdir(parents=True)
    _git(root, "init", "-q")

    # commit0: base state, node non-canonical. Model + replay input land here so both
    # exist at base_ref for the legacy-side replay.
    _write(contract_file, SINGLE_BINDING_CONTRACT)
    _write(model_file, DEMO_MODEL)
    _write(
        handler_file, DIVERGING_LEGACY_HANDLER if diverging_legacy else LEGACY_HANDLER
    )
    _write(
        input_file, json.dumps(REPLAY_INPUT_PAYLOAD, indent=2, sort_keys=True) + "\n"
    )
    _write(baseline_path, 'NON_CANONICAL = ("testpkg.nodes.node_demo_compute",)\n')
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base state (non-canonical)", author=AUTHOR_X)
    anchor_x = _git(root, "rev-parse", "HEAD")

    # commit1: trivial anchor == origin/dev pre-flip == base_ref.
    _write(root / "docs" / "anchor.md", "pre-flip base\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "pre-flip anchor", author=AUTHOR_Y)
    base_ref = _git(root, "rev-parse", "HEAD")

    # commit2: the flip. Canonical handler first (optionally ruff-formatted), THEN hash
    # it, THEN mint the receipt (S1 ordering), THEN shrink the baseline.
    _write(handler_file, CANONICAL_HANDLER if formatted else UNFORMATTED_HANDLER)
    if formatted:
        _ruff_format(handler_file)
    handler_sha = _sha256_file(handler_file)

    input_hash = "sha256:" + hashlib.sha256(input_file.read_bytes()).hexdigest()
    _write(
        receipts_dir / f"{NODE_ID}.json",
        json.dumps(_adequacy_receipt(handler_sha, [input_hash]), indent=2),
    )

    equiv_path = receipts_dir / f"{NODE_ID}.equivalence.json"
    # Seed a skeleton carrying only the declaration, then DERIVE the faithful artifact by
    # rerunning the real producer (exactly what the gate will do), and commit its bytes.
    skeleton = {
        "node_id": NODE_ID,
        "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2,
        "declaration": _v2_declaration(base_ref),
        "selected_input_hashes": [],
        "status": "unknown",
    }
    _write(equiv_path, json.dumps(skeleton, indent=2))
    produced, detail = eqp.produce(NODE_ID, equiv_path, root, src_root, base_ref)
    assert produced is not None, f"fixture producer failed: {detail}"
    equiv_path.write_bytes(produced)

    _write(baseline_path, "NON_CANONICAL = ()\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "flip to canonical def-B", author=AUTHOR_X)
    def_b_commit = _git(root, "rev-parse", "HEAD")

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
    # Assertion 6 genuinely RAN the byte-compare producer rerun (not grandfathered):
    assert result.grandfathered is False
    a6 = next(o for o in result.outcomes if o.index == 6)
    assert a6.name == "reproducible-equivalence"
    assert "byte-identical" in a6.detail
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


def test_seed_c_forged_pass_over_diverging_replay_fails_assertion_6(
    tmp_path: Path,
) -> None:
    """The E1 attack: a golden that forges status=pass while the real replay diverges.

    ``verify_equivalence_replay`` (assertion 2's transitive dependency) TRUSTS
    status=pass, so a forged-pass golden clears assertions 1-5. Assertion 6 reruns the
    producer, the honest replay is status=fail (legacy mutates a field), and the
    byte-compare rejects. Author identity is irrelevant — this is the whole point.
    """
    repo = build_flip_repo(tmp_path, diverging_legacy=True)
    equiv_path = repo.receipts_dir / f"{NODE_ID}.equivalence.json"
    raw = json.loads(equiv_path.read_text())
    assert raw["status"] == "fail", "diverging fixture must honestly be status=fail"
    raw["status"] = "pass"  # the hand-authored lie
    equiv_path.write_text(json.dumps(raw, indent=2))

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 6, result.reason
    assert "byte-compare FAILED" in result.reason
    assert "status" in result.reason


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
# 4. Guardrail: assertion 6 fails CLOSED when the replay declaration is absent, or
#    when the legacy side is collapsed onto HEAD.
# --------------------------------------------------------------------------- #


def test_new_equivalence_flip_without_declaration_fails_assertion_6(
    tmp_path: Path,
) -> None:
    """A NEW flip carrying a bare v1 artifact (no declaration) cannot be reproduced."""
    repo = build_flip_repo(tmp_path)
    equiv_path = repo.receipts_dir / f"{NODE_ID}.equivalence.json"
    faithful = json.loads(equiv_path.read_text())
    # Downgrade to the legacy v1 shape: right node + status=pass + the SAME derived
    # hashes (so the assertion-2 receipt/proof binding still passes), but NO declaration
    # and no v2 schema — so assertion 6's producer rerun cannot reproduce it.
    equiv_path.write_text(
        json.dumps(
            {
                "node_id": NODE_ID,
                "selected_input_hashes": faithful["selected_input_hashes"],
                "status": "pass",
            },
            indent=2,
        )
    )

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 6, result.reason
    assert "receipt_schema" in result.reason


def test_legacy_base_ref_not_ancestor_of_gate_base_fails_assertion_6(
    tmp_path: Path,
) -> None:
    """base_ref must be pre-flip: a descendant of the gate base collapses the legacy side."""
    repo = build_flip_repo(tmp_path)
    equiv_path = repo.receipts_dir / f"{NODE_ID}.equivalence.json"
    raw = json.loads(equiv_path.read_text())
    # Point base_ref at the flip commit itself — NOT an ancestor of the gate base
    # (repo.base_ref == commit1); commit2 is a descendant, so the guard must fire.
    raw["declaration"]["base_ref"] = repo.def_b_commit
    equiv_path.write_text(json.dumps(raw, indent=2))

    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 6, result.reason
    assert "not an ancestor" in result.reason


def test_missing_adequacy_receipt_fails_closed_assertion_1(tmp_path: Path) -> None:
    repo = build_flip_repo(tmp_path)
    (repo.receipts_dir / f"{NODE_ID}.json").unlink()
    result = _run(repo)
    assert result.ok is False
    assert result.failed_assertion == 1
    assert "absent" in result.reason
