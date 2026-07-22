# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Focused unit tests for the deterministic equivalence producer (OMN-14905).

The end-to-end ACCEPT/REJECT behavior through the real gate lives in
``test_verify_flip_bundle.py`` (which builds real git repos and executes real handlers).
These tests cover the producer's pure surface and fail-closed pre-git validation branches
directly: canonical encoding determinism, declaration schema enforcement, and the
byte_compare-on-producer-failure path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import equivalence_producer as eqp

pytestmark = pytest.mark.unit

NODE = "testpkg.nodes.node_demo_compute"


def _valid_declaration() -> dict[str, object]:
    return {
        "base_ref": "abc123",
        "legacy_handler_module": f"{NODE}.handler",
        "legacy_handler_symbol": "HandlerDemoCompute",
        "legacy_entrypoint": "run",
        "canonical_handler_module": f"{NODE}.handler",
        "canonical_handler_symbol": "HandlerDemoCompute",
        "canonical_entrypoint": "handle",
        "input_model": f"{NODE}.model.ModelDemoInput",
        "replay_inputs": ["scripts/ci/equivalence_inputs/case.json"],
        "volatile_mask": [],
    }


def _write_artifact(tmp_path: Path, body: dict[str, object]) -> Path:
    art = tmp_path / f"{NODE}.equivalence.json"
    art.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return art


def test_canonical_bytes_is_sorted_indented_and_newline_terminated() -> None:
    a = eqp.canonical_bytes({"b": 2, "a": 1})
    b = eqp.canonical_bytes({"a": 1, "b": 2})
    assert a == b  # key order does not matter
    assert a.endswith(b"\n")
    assert a.decode() == '{\n  "a": 1,\n  "b": 2\n}\n'


def test_produce_rejects_node_id_mismatch(tmp_path: Path) -> None:
    art = _write_artifact(
        tmp_path,
        {
            "node_id": "other.node",
            "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2,
            "declaration": _valid_declaration(),
        },
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "node_id mismatch" in reason


def test_produce_rejects_non_v2_schema(tmp_path: Path) -> None:
    art = _write_artifact(
        tmp_path,
        {"node_id": NODE, "selected_input_hashes": [], "status": "pass"},
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "receipt_schema" in reason


def test_produce_rejects_missing_declaration_key(tmp_path: Path) -> None:
    decl = _valid_declaration()
    del decl["input_model"]
    art = _write_artifact(
        tmp_path,
        {
            "node_id": NODE,
            "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2,
            "declaration": decl,
        },
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "missing key" in reason and "input_model" in reason


def test_produce_rejects_unknown_declaration_key(tmp_path: Path) -> None:
    decl = _valid_declaration()
    decl["surprise"] = "extra"
    art = _write_artifact(
        tmp_path,
        {
            "node_id": NODE,
            "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2,
            "declaration": decl,
        },
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "unknown key" in reason and "surprise" in reason


def test_produce_rejects_empty_replay_inputs(tmp_path: Path) -> None:
    decl = _valid_declaration()
    decl["replay_inputs"] = []
    art = _write_artifact(
        tmp_path,
        {
            "node_id": NODE,
            "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2,
            "declaration": decl,
        },
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "replay_inputs" in reason


def test_produce_rejects_missing_declaration_block(tmp_path: Path) -> None:
    art = _write_artifact(
        tmp_path,
        {"node_id": NODE, "receipt_schema": eqp.EQUIVALENCE_SCHEMA_V2},
    )
    produced, reason = eqp.produce(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert produced is None
    assert "no declaration" in reason


def test_produce_rejects_unreadable_artifact(tmp_path: Path) -> None:
    produced, reason = eqp.produce(
        NODE, tmp_path / "absent.json", tmp_path, tmp_path, "origin/dev"
    )
    assert produced is None
    assert "unreadable" in reason


def test_byte_compare_fails_when_producer_cannot_reproduce(tmp_path: Path) -> None:
    # Non-v2 artifact -> produce returns None -> byte_compare is a hard REJECT.
    art = _write_artifact(
        tmp_path,
        {"node_id": NODE, "selected_input_hashes": [], "status": "pass"},
    )
    ok, reason = eqp.byte_compare(NODE, art, tmp_path, tmp_path, "origin/dev")
    assert ok is False
    assert "could not reproduce" in reason
