# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Real-git proofs and falsifiers for no-legacy handler flips (OMN-20298)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import scripts.ci.canonical_handler_shape as mod
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from scripts.ci.verify_flip_bundle import _assert_typed_adequacy

NODE_ID = "pkgx.nodes.node_a"
HANDLER_MODULE = f"{NODE_ID}.handlers.handler_a"
NODE_REL = "src/pkgx/nodes/node_a"
CONTRACT_TEST = "tests/test_node_a_contract.py::test_handle_roundtrip"
CONTRACT = "name: node_a\nnode_type: orchestrator\n"
BINDING = "handler: {module: pkgx.nodes.node_a.handlers.handler_a, class: HandlerA}\n"
CANONICAL_HANDLER = """from pydantic import BaseModel

class ModelReq(BaseModel):
    x: int

class ModelResp(BaseModel):
    y: int

class HandlerA:
    def handle(self, request: ModelReq) -> ModelResp:
        return ModelResp(y=request.x)
"""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    ).stdout.strip()


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(
        root,
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=t",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        message,
    )
    return _git(root, "rev-parse", "HEAD")


def _add_legacy_handler(root: Path) -> None:
    node = root / NODE_REL
    handlers = node / "handlers"
    handlers.mkdir(exist_ok=True)
    (handlers / "__init__.py").write_text("", encoding="utf-8")
    (handlers / "handler_a.py").write_text(
        "class HandlerA:\n    def execute(self, envelope):\n        return envelope\n",
        encoding="utf-8",
    )
    (node / "contract.yaml").write_text(CONTRACT + BINDING, encoding="utf-8")


def _build_repo(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    legacy: str = "none",
    live_handler: bool = False,
) -> tuple[Path, str]:
    root.mkdir()
    _git(root, "init", "-q")
    node = root / NODE_REL
    node.mkdir(parents=True)
    for package in (root / "src/pkgx", root / "src/pkgx/nodes", node):
        (package / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (node / "consumer.py").write_text(
        "def main() -> None:\n    pass\n", encoding="utf-8"
    )
    (node / "contract.yaml").write_text(CONTRACT, encoding="utf-8")
    if legacy == "bound":
        _add_legacy_handler(root)
    elif legacy == "bridge":
        (node / "consumer.py").write_text(
            "class Bridge:\n    def handle(self, event):\n        return event\n",
            encoding="utf-8",
        )
    base = _commit(root, "BASE")
    if live_handler:
        _add_legacy_handler(root)
        _commit(root, "Add a legacy handler after the handlerless commit")
    _git(root, "branch", "dev")

    (node / "consumer.py").unlink()
    handlers = node / "handlers"
    handlers.mkdir(exist_ok=True)
    (handlers / "__init__.py").write_text("", encoding="utf-8")
    (handlers / "handler_a.py").write_text(CANONICAL_HANDLER, encoding="utf-8")
    (node / "contract.yaml").write_text(CONTRACT + BINDING, encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_node_a_contract.py").write_text(
        f"from {HANDLER_MODULE} import HandlerA, ModelReq\n\n"
        "def test_handle_roundtrip() -> None:\n"
        "    assert HandlerA().handle(ModelReq(x=1)).y == 1\n",
        encoding="utf-8",
    )
    _commit(root, "HEAD: canonical handler and contract test")
    (root / "receipts").mkdir()
    monkeypatch.setattr(mod, "SRC_ROOT", root / "src")
    monkeypatch.setattr(mod, "RECEIPTS_DIR", root / "receipts")
    monkeypatch.setattr(mod, "BASE_REF", "dev")
    return root, base


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    return _build_repo(tmp_path / "repo", monkeypatch)


def _executor(executed: bool = True, green: bool = True) -> mod.ParityExecutor:
    def execute(_node_id: str, _test_ids: tuple[str, ...]) -> mod.ModelParityVerdict:
        return mod.ModelParityVerdict(executed=executed, green=green, detail="stub")

    return execute


def _write_receipt(root: Path, base: str, **overrides: object) -> Path:
    body = {
        "receipt_schema": "adequacy_receipt.no_legacy.v1",
        "node_id": NODE_ID,
        "legacy_handler": "none",
        "base_ref": base,
        "base_node_files": sorted(
            _git(
                root, "ls-tree", "-r", "--name-only", base, "--", NODE_REL
            ).splitlines()
        ),
        "handler_module": HANDLER_MODULE,
        "handler_module_sha256": mod._sha256_file(
            root / NODE_REL / "handlers/handler_a.py"
        ),
        "contract_tests": [CONTRACT_TEST],
        "recorded_at": "2026-10-13T00:00:00Z",
    }
    body.update(overrides)
    path = root / "receipts" / f"{NODE_ID}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _canon() -> mod.ModelHandlerShapeFinding:
    return mod.ModelHandlerShapeFinding(
        node_id=NODE_ID,
        category="canonical",
        is_canonical=True,
        handler_module=HANDLER_MODULE,
    )


@pytest.mark.unit
def test_no_legacy_flip_with_valid_receipt_passes(
    repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_receipt(*repo)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is True, reason
    assert reason.startswith("no-legacy:")
    assert "contract-tests-executed-green" in reason

    monkeypatch.setattr(mod, "default_parity_executor", _executor())
    result = mod.evaluate([_canon()], baseline=[], base_baseline=[NODE_ID])
    assert result.failed is False
    assert NODE_ID in result.proven_flips


@pytest.mark.unit
def test_no_legacy_flip_without_receipt_fails(
    repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _base = repo
    assert not (root / "receipts" / f"{NODE_ID}.json").exists()
    monkeypatch.setattr(mod, "default_parity_executor", _executor())
    findings = [_canon()]
    result = mod.evaluate(findings, baseline=[], base_baseline=[NODE_ID])
    assert NODE_ID in result.unproven_flips
    assert result.failed
    failure = mod._format_failure(result, findings)
    assert "legacy_handler: none" in failure
    assert "no adequacy receipt at" in failure


@pytest.mark.unit
@pytest.mark.parametrize("legacy", ["bound", "bridge"])
def test_node_that_had_a_handler_cannot_use_no_legacy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legacy: str
) -> None:
    root, base = _build_repo(tmp_path / "repo", monkeypatch, legacy=legacy)
    _write_receipt(root, base)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "legacy handler existed" in reason


@pytest.mark.unit
def test_old_handlerless_commit_cannot_be_cited_past_a_live_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = _build_repo(tmp_path / "repo", monkeypatch, live_handler=True)
    _write_receipt(root, base)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "live merge base" in reason


@pytest.mark.unit
def test_base_node_files_must_match_git_listing(repo: tuple[Path, str]) -> None:
    root, base = repo
    files = _git(
        root, "ls-tree", "-r", "--name-only", base, "--", NODE_REL
    ).splitlines()
    _write_receipt(root, base, base_node_files=files[1:])
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "does not match git ls-tree" in reason


@pytest.mark.unit
@pytest.mark.parametrize(
    ("executed", "green", "expected_reason"),
    [(True, False, "NOT GREEN"), (False, True, "UNEXECUTED")],
)
def test_contract_tests_must_execute_green(
    repo: tuple[Path, str], executed: bool, green: bool, expected_reason: str
) -> None:
    _write_receipt(*repo)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID,
        HANDLER_MODULE,
        parity_executor=_executor(executed=executed, green=green),
    )
    assert ok is False
    assert expected_reason in reason


@pytest.mark.unit
def test_contract_test_file_must_name_the_node(repo: tuple[Path, str]) -> None:
    root, base = repo
    (root / "tests/test_unrelated.py").write_text(
        "def test_unrelated() -> None:\n    assert 1 == 1\n", encoding="utf-8"
    )
    _commit(root, "Add an unrelated test")
    _write_receipt(
        root, base, contract_tests=["tests/test_unrelated.py::test_unrelated"]
    )
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "never names" in reason


@pytest.mark.unit
def test_legacy_handler_other_than_none_is_refused(repo: tuple[Path, str]) -> None:
    _write_receipt(*repo, legacy_handler=f"{NODE_ID}.consumer")
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "only 'none'" in reason


@pytest.mark.unit
def test_stale_handler_sha_refused(repo: tuple[Path, str]) -> None:
    _write_receipt(*repo, handler_module_sha256="sha256:00")
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "stale receipt" in reason


@pytest.mark.unit
def test_base_ref_must_be_ancestor_of_head(repo: tuple[Path, str]) -> None:
    root, _base = repo
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--orphan", "unrelated")
    unrelated = _commit(root, "Unrelated root commit")
    _git(root, "checkout", "--detach", head)
    _write_receipt(root, unrelated)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "not an ancestor" in reason


@pytest.mark.unit
def test_seam_gate_typed_model_accepts_no_legacy_receipt(
    repo: tuple[Path, str],
) -> None:
    root, base = repo
    _write_receipt(root, base)
    ok, reason = _assert_typed_adequacy(NODE_ID, root / "receipts")
    assert ok is True, reason
    assert "ModelNoLegacyAdequacyReceipt" in reason

    _write_receipt(root, base, contract_tests=[])
    ok, reason = _assert_typed_adequacy(NODE_ID, root / "receipts")
    assert ok is False
    assert "ModelNoLegacyAdequacyReceipt invariants violated" in reason
    assert "contract_tests" in reason


@pytest.mark.unit
def test_existing_handler_path_unchanged(repo: tuple[Path, str]) -> None:
    root, _base = repo
    receipt = {
        "receipt_schema": "adequacy_receipt.v1",
        "node_id": NODE_ID,
        "handler_module": HANDLER_MODULE,
        "handler_module_sha256": mod._sha256_file(
            root / NODE_REL / "handlers/handler_a.py"
        ),
        "recorded_at": "2026-10-13T00:00:00Z",
        "candidate_count": 1,
        "selected_count": 1,
        "selected_input_hashes": ["sha256:input"],
        "branch_coverage_pct": 100.0,
        "coverage_target": 80.0,
        "meets_target": True,
    }
    (root / "receipts" / f"{NODE_ID}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert reason.startswith(("adequacy:", "proof:"))
    assert "no equivalence-replay" in reason
    assert "no hand-flip proof" in reason


@pytest.mark.unit
def test_landed_no_legacy_receipt_remains_valid_on_descendants(
    repo: tuple[Path, str],
) -> None:
    root, base = repo
    _write_receipt(root, base)
    _commit(root, "Land the canonical handler with its no-legacy receipt")
    _git(root, "branch", "-f", "dev", "HEAD")
    (root / "unrelated.txt").write_text("unrelated change\n", encoding="utf-8")
    _commit(root, "Unrelated descendant change")

    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is True, reason
    assert "contract-tests-executed-green" in reason


@pytest.mark.unit
@pytest.mark.parametrize("change", ["receipt", "handler"])
def test_landed_no_legacy_proof_cannot_be_replaced(
    repo: tuple[Path, str], change: str
) -> None:
    root, base = repo
    receipt = _write_receipt(root, base)
    _commit(root, "Land the canonical handler with its no-legacy receipt")
    _git(root, "branch", "-f", "dev", "HEAD")
    if change == "handler":
        handler = root / NODE_REL / "handlers/handler_a.py"
        handler.write_text(CANONICAL_HANDLER.replace("y=request.x", "y=request.x + 1"))
        _write_receipt(root, base)
    else:
        raw = json.loads(receipt.read_text(encoding="utf-8"))
        raw["recorded_at"] = "2026-10-17T00:00:00Z"
        receipt.write_text(json.dumps(raw), encoding="utf-8")
    _commit(root, "Replace previously landed proof inputs")

    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "live merge base" in reason


@pytest.mark.unit
def test_landed_no_legacy_receipt_still_executes_contract_tests(
    repo: tuple[Path, str],
) -> None:
    root, base = repo
    _write_receipt(root, base)
    _commit(root, "Land the canonical handler with its no-legacy receipt")
    _git(root, "branch", "-f", "dev", "HEAD")

    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor(green=False)
    )
    assert ok is False
    assert "NOT GREEN" in reason


def _land_flip(root: Path, base: str) -> str:
    """Squash the receipt into the flip commit and move dev onto it (a merged flip)."""
    _write_receipt(root, base)
    _git(root, "add", "--all")
    _git(
        root,
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=t",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "--amend",
        "--no-edit",
    )
    landed = _git(root, "rev-parse", "HEAD")
    _git(root, "branch", "-f", "dev", landed)
    return landed


@pytest.mark.unit
def test_landed_no_legacy_flip_passes_after_merge(
    repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = repo
    _land_flip(root, base)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is True, reason

    # The change that drops the landed node from the baseline is a proven flip.
    monkeypatch.setattr(mod, "default_parity_executor", _executor())
    result = mod.evaluate([_canon()], baseline=[], base_baseline=[NODE_ID])
    assert result.failed is False
    assert NODE_ID in result.proven_flips


@pytest.mark.unit
def test_landed_flip_over_a_base_handler_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = _build_repo(tmp_path / "repo", monkeypatch, live_handler=True)
    _land_flip(root, base)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "live merge base" in reason
    assert "before the receipt landed" in reason


@pytest.mark.unit
def test_receipt_landed_after_a_different_handler_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = _build_repo(tmp_path / "repo", monkeypatch, live_handler=True)
    _write_receipt(root, base)
    landed = _commit(root, "Receipt lands after a legacy and a canonical handler")
    _git(root, "branch", "-f", "dev", landed)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "before the receipt landed" in reason


@pytest.mark.unit
def test_node_changed_after_the_flip_landed_is_refused(
    repo: tuple[Path, str],
) -> None:
    root, base = repo
    _land_flip(root, base)
    (root / NODE_REL / "extra.py").write_text("X = 1\n", encoding="utf-8")
    _commit(root, "Change the node after the flip landed")
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "changed since" in reason


@pytest.mark.unit
def test_unlanded_receipt_keeps_the_live_base_refusal(
    repo: tuple[Path, str],
) -> None:
    root, base = repo
    # dev already holds the handler commit, but the receipt never landed there.
    _git(root, "branch", "-f", "dev", "HEAD")
    _write_receipt(root, base)
    ok, reason = mod.verify_flip_receipt(
        NODE_ID, HANDLER_MODULE, parity_executor=_executor()
    )
    assert ok is False
    assert "did not land on the live merge base" in reason
