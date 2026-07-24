# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the RSD provenance-stamp fail-closed gate (OMN-15011).

RED-first: ``test_new_node_without_stamp_hard_fails`` proves the gate rejects a
deliberately unstamped new node (the exact vulnerability the OMN-15011 audit
found: nothing today proves a shape-canonical node was RSD-generated).
``test_new_node_with_valid_machine_stamp_passes`` then proves the SAME node
passes once stamped — the RED/GREEN pair required by acceptance criteria (2)/(3).
``test_tampered_content_forged_stamp_is_rejected`` covers acceptance (4): a
stamp whose claimed digest no longer matches the live file content is treated
as unproven, not trusted.

``TestSeamContractWithOmnimarketEmitter`` is the other half of the cross-repo
seam test described in ``omnimarket``'s
``tests/nodes/node_hybrid_codegen_orchestrator/test_handler_hybrid_codegen_orchestrator.py::TestProvenanceStampSeam``
(the two repos cannot co-import each other; the seam is proven at the schema
level in each repo independently, mirroring the existing seam-match pattern in
``omnimarket.codegen.models``).
"""

from __future__ import annotations

import hashlib
import json

import pytest

import scripts.ci.rsd_provenance_stamp as mod
from scripts.ci.rsd_provenance_stamp import (
    STAMP_FILENAME,
    ModelProvenanceFinding,
    classify_all,
    classify_node,
    current_unstamped,
    evaluate,
    load_base_baseline,
    load_baseline,
    write_baseline,
)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_node(
    tmp_path,
    node_name: str = "node_demo",
    *,
    contract_content: str = "name: node_demo\n",
    stamp: dict[str, object] | None = None,
) -> tuple[object, str]:
    """Create ``<tmp_path>/omnibase_core/nodes/<node_name>/contract.yaml``.

    Returns ``(contract_path, node_id)``. Writes ``stamp`` as JSON alongside if
    given; writes nothing (RED case) when ``stamp`` is ``None``.
    """
    node_dir = tmp_path / "omnibase_core" / "nodes" / node_name
    node_dir.mkdir(parents=True)
    contract_path = node_dir / "contract.yaml"
    contract_path.write_text(contract_content, encoding="utf-8")
    if stamp is not None:
        (node_dir / STAMP_FILENAME).write_text(
            json.dumps(stamp, indent=2), encoding="utf-8"
        )
    node_id = f"omnibase_core.nodes.{node_name}"
    return contract_path, node_id


def _valid_machine_stamp(contract_content: str, **overrides: object) -> dict:
    stamp = {
        "receipt_schema": "rsd_provenance_stamp.v1",
        "generated_by": "rsd_delegation",
        "producer_node": "node_hybrid_codegen_orchestrator",
        "run_id": "run-abc-123",
        "node_name": "NodeDemo",
        "files_sha256": {"contract.yaml": _sha(contract_content)},
    }
    stamp.update(overrides)
    return stamp


@pytest.fixture(autouse=True)
def _patch_src_root(tmp_path, monkeypatch):
    """Isolate every test's classify_node/_node_package resolution to tmp_path."""
    monkeypatch.setattr(mod, "SRC_ROOT", tmp_path)


# --------------------------------------------------------------------------- #
# RED-first: the exact vulnerability OMN-15011 identified
# --------------------------------------------------------------------------- #


def test_new_node_without_stamp_hard_fails(tmp_path) -> None:
    """RED: a brand-new node with no .rsd_provenance.json is unstamped."""
    contract_path, node_id = _make_node(tmp_path, stamp=None)
    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "missing"

    result = evaluate([finding], baseline=[], base_baseline=[])
    assert result.failed is True
    assert node_id in result.new_unstamped


def test_new_node_with_valid_machine_stamp_passes(tmp_path) -> None:
    """GREEN: the SAME node, now carrying a valid rsd_delegation stamp."""
    contract_content = "name: node_demo\n"
    contract_path, node_id = _make_node(
        tmp_path,
        contract_content=contract_content,
        stamp=_valid_machine_stamp(contract_content),
    )
    finding = classify_node(contract_path)
    assert finding.is_stamped is True
    assert finding.category == "rsd_delegation"

    result = evaluate([finding], baseline=[], base_baseline=[])
    assert result.failed is False
    assert node_id not in result.new_unstamped


def test_tampered_content_forged_stamp_is_rejected(tmp_path) -> None:
    """Acceptance (4): a stamp whose recorded digest no longer matches the live
    file content is a stale/forged stamp -- the gate recomputes, never trusts."""
    original = "name: node_demo\n"
    contract_path, _ = _make_node(
        tmp_path, contract_content=original, stamp=_valid_machine_stamp(original)
    )
    # Tamper with contract.yaml AFTER the stamp was minted.
    contract_path.write_text(original + "extra: tampered\n", encoding="utf-8")

    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "stamp_hash_mismatch"
    assert "stale or forged" in (finding.detail or "")


# --------------------------------------------------------------------------- #
# Classification -- machine stamp completeness
# --------------------------------------------------------------------------- #


def test_missing_producer_node_is_incomplete(tmp_path) -> None:
    content = "name: node_demo\n"
    stamp = _valid_machine_stamp(content)
    stamp["producer_node"] = ""
    contract_path, _ = _make_node(tmp_path, contract_content=content, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "incomplete_machine_stamp"


def test_missing_run_id_is_incomplete(tmp_path) -> None:
    content = "name: node_demo\n"
    stamp = _valid_machine_stamp(content)
    del stamp["run_id"]
    contract_path, _ = _make_node(tmp_path, contract_content=content, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "incomplete_machine_stamp"


def test_files_sha256_must_cover_contract_yaml(tmp_path) -> None:
    content = "name: node_demo\n"
    stamp = _valid_machine_stamp(content)
    stamp["files_sha256"] = {"handler.py": _sha("x")}  # contract.yaml missing
    contract_path, _ = _make_node(tmp_path, contract_content=content, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "incomplete_machine_stamp"
    assert "contract.yaml" in (finding.detail or "")


def test_referenced_file_absent_on_disk_fails(tmp_path) -> None:
    content = "name: node_demo\n"
    stamp = _valid_machine_stamp(content)
    stamp["files_sha256"]["handler.py"] = _sha("never written")
    contract_path, _ = _make_node(tmp_path, contract_content=content, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "stamp_file_missing"


# --------------------------------------------------------------------------- #
# Classification -- hand-authored exception path (OMN-14781 sanctioned)
# --------------------------------------------------------------------------- #


def test_hand_authored_with_valid_ticket_passes(tmp_path) -> None:
    stamp = {
        "receipt_schema": "rsd_provenance_stamp.v1",
        "generated_by": "hand_authored",
        "ticket": "OMN-14781",
    }
    contract_path, _ = _make_node(tmp_path, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.is_stamped is True
    assert finding.category == "hand_authored"
    assert finding.detail == "ticket=OMN-14781"


def test_hand_authored_without_ticket_fails(tmp_path) -> None:
    stamp = {
        "receipt_schema": "rsd_provenance_stamp.v1",
        "generated_by": "hand_authored",
    }
    contract_path, _ = _make_node(tmp_path, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "hand_authored_bad_ticket"


def test_hand_authored_malformed_ticket_fails(tmp_path) -> None:
    stamp = {
        "receipt_schema": "rsd_provenance_stamp.v1",
        "generated_by": "hand_authored",
        "ticket": "not-a-ticket",
    }
    contract_path, _ = _make_node(tmp_path, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "hand_authored_bad_ticket"


# --------------------------------------------------------------------------- #
# Classification -- schema / parse failures (fail-closed: absent means FAIL)
# --------------------------------------------------------------------------- #


def test_absent_stamp_file_fails_closed(tmp_path) -> None:
    contract_path, _ = _make_node(tmp_path, stamp=None)
    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "missing"


def test_unparseable_stamp_fails_closed(tmp_path) -> None:
    contract_path, _ = _make_node(tmp_path, stamp=None)
    (contract_path.parent / STAMP_FILENAME).write_text(
        "{not valid json", encoding="utf-8"
    )
    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "unparseable"


def test_stamp_that_is_a_json_array_not_object_fails_closed(tmp_path) -> None:
    contract_path, _ = _make_node(tmp_path, stamp=None)
    (contract_path.parent / STAMP_FILENAME).write_text("[1, 2, 3]", encoding="utf-8")
    finding = classify_node(contract_path)
    assert finding.is_stamped is False
    assert finding.category == "unparseable"


def test_wrong_schema_version_fails_closed(tmp_path) -> None:
    stamp = _valid_machine_stamp("name: x\n")
    stamp["receipt_schema"] = "rsd_provenance_stamp.v0-draft"
    contract_path, _ = _make_node(tmp_path, contract_content="name: x\n", stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "bad_schema"


def test_unknown_generated_by_fails_closed(tmp_path) -> None:
    stamp = {"receipt_schema": "rsd_provenance_stamp.v1", "generated_by": "vibe_coded"}
    contract_path, _ = _make_node(tmp_path, stamp=stamp)
    finding = classify_node(contract_path)
    assert finding.category == "unknown_generated_by"


# --------------------------------------------------------------------------- #
# Ratchet -- baseline exemption, WARN vs HARD-FAIL, growth
# --------------------------------------------------------------------------- #


def test_baselined_unstamped_node_warns_not_fails(tmp_path) -> None:
    _, node_id = _make_node(tmp_path, stamp=None)
    finding = ModelProvenanceFinding(
        node_id=node_id, is_stamped=False, category="missing", detail=None
    )
    result = evaluate([finding], baseline=[node_id], base_baseline=[node_id])
    assert result.failed is False
    assert node_id in result.warn_baselined


def test_baseline_growth_hard_fails(tmp_path) -> None:
    # Working baseline hand-adds an entry absent from git-BASE -> illegal growth,
    # unconditionally (no proof can rescue growth -- it is a bounded allowlist).
    result = evaluate(
        [], baseline=["omnibase_core.nodes.node_sneaky"], base_baseline=[]
    )
    assert result.failed is True
    assert "omnibase_core.nodes.node_sneaky" in result.baseline_growth


def test_baseline_shrink_needs_no_extra_proof(tmp_path) -> None:
    # A node leaves the baseline by acquiring a real stamp -- classify_node's own
    # recompute IS the proof; evaluate() requires nothing further.
    content = "name: node_demo\n"
    _, node_id = _make_node(
        tmp_path, contract_content=content, stamp=_valid_machine_stamp(content)
    )
    finding = ModelProvenanceFinding(
        node_id=node_id, is_stamped=True, category="rsd_delegation", detail="ok"
    )
    result = evaluate([finding], baseline=[], base_baseline=[node_id])
    assert result.failed is False
    assert result.baseline_growth == ()


def test_base_baseline_none_skips_growth_check() -> None:
    # First-ever landing of the gate: baseline absent at git-BASE -> None, not
    # [], so this PR's own freshly-generated baseline is never treated as growth.
    result = evaluate(
        [], baseline=["omnibase_core.nodes.node_legacy"], base_baseline=None
    )
    assert result.failed is False
    assert result.baseline_growth == ()


# --------------------------------------------------------------------------- #
# Baseline round-trip (write_baseline / load_baseline / load_base_baseline)
# --------------------------------------------------------------------------- #


def test_write_and_load_baseline_roundtrip(tmp_path) -> None:
    baseline_path = tmp_path / "rsd_provenance_stamp_baseline.py"
    write_baseline(
        ["omnibase_core.nodes.node_a", "omnibase_core.nodes.node_b"], baseline_path
    )
    assert load_baseline(baseline_path) == [
        "omnibase_core.nodes.node_a",
        "omnibase_core.nodes.node_b",
    ]


def test_load_baseline_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_baseline(tmp_path / "does_not_exist.py")


def test_load_base_baseline_absent_at_ref_returns_none(tmp_path, monkeypatch) -> None:
    # A path outside any git repo -> _git_repo_root returns None -> None.
    result = load_base_baseline(
        tmp_path / "rsd_provenance_stamp_baseline.py", "origin/dev"
    )
    assert result is None


# --------------------------------------------------------------------------- #
# classify_all / current_unstamped over a small synthetic tree
# --------------------------------------------------------------------------- #


def test_classify_all_and_current_unstamped(tmp_path, monkeypatch) -> None:
    content = "name: node_a\n"
    _make_node(
        tmp_path,
        node_name="node_a",
        contract_content=content,
        stamp=_valid_machine_stamp(content),
    )
    _make_node(tmp_path, node_name="node_b", stamp=None)
    monkeypatch.setattr(mod, "NODES_GLOB", "omnibase_core/**/nodes/**/contract.yaml")

    findings = classify_all()
    assert {f.node_id for f in findings} == {
        "omnibase_core.nodes.node_a",
        "omnibase_core.nodes.node_b",
    }
    assert current_unstamped(findings) == ["omnibase_core.nodes.node_b"]


# --------------------------------------------------------------------------- #
# Cross-repo seam contract (OMN-15011 seam requirement / OMN-14208 guard)
# --------------------------------------------------------------------------- #


class TestSeamContractWithOmnimarketEmitter:
    """The ``.rsd_provenance.json`` field set this gate reads MUST equal,
    field-for-field, what omnimarket's ``node_hybrid_codegen_orchestrator``
    handler (``_provenance_stamp_json``) emits. omnibase_core cannot import
    omnimarket (layering: compat -> core -> spi -> infra; omnimarket sits
    outside that chain entirely), so this locks the CONSUMING side of the same
    golden schema the emitter's own seam test
    (``TestProvenanceStampSeam::test_provenance_stamp_schema_matches_gate_seam_contract``)
    locks on the PRODUCING side -- both sides assert the identical field set
    independently, so drift on either side breaks its own repo's suite.
    """

    def test_gate_accepts_the_exact_shape_the_emitter_produces(self, tmp_path) -> None:
        # Byte-for-byte the JSON omnimarket's _provenance_stamp_json() produces
        # for a real run (see that function + its seam test for the source of
        # truth on the field set/values).
        contract_yaml = "name: node_greeter_compute\n"
        handler_py = "class Handler: ..."
        metadata_yaml = 'name: node_greeter_compute\nversion: "1.0.0"\n'
        emitted_stamp = {
            "receipt_schema": "rsd_provenance_stamp.v1",
            "generated_by": "rsd_delegation",
            "producer_node": "node_hybrid_codegen_orchestrator",
            "run_id": "run-abc-123",
            "node_name": "NodeGreeterCompute",
            "files_sha256": {
                "handler.py": _sha(handler_py),
                "contract.yaml": _sha(contract_yaml),
                "metadata.yaml": _sha(metadata_yaml),
            },
        }
        node_dir = tmp_path / "omnibase_core" / "nodes" / "node_greeter_compute"
        node_dir.mkdir(parents=True)
        (node_dir / "contract.yaml").write_text(contract_yaml, encoding="utf-8")
        (node_dir / "handler.py").write_text(handler_py, encoding="utf-8")
        (node_dir / "metadata.yaml").write_text(metadata_yaml, encoding="utf-8")
        (node_dir / STAMP_FILENAME).write_text(
            json.dumps(emitted_stamp, indent=2), encoding="utf-8"
        )

        finding = classify_node(node_dir / "contract.yaml")
        assert finding.is_stamped is True
        assert finding.category == "rsd_delegation"
