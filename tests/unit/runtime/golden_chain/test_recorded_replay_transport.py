# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the canonical golden-chain replay harness (OMN-13499).

These prove the load-bearing properties:

  * replay returns recorded bytes ONLY for the matching concrete route + request,
  * a WRONG model / endpoint / token budget FAILS with a named failure class
    (replay is evidence, not authority — the routing-failure proof),
  * a delegation tier name as model_key is hard-rejected,
  * empty / echo / malformed fixtures fail closed,
  * record mode is operator-gated (PR CI cannot record).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.models.runtime.golden_chain.model_golden_chain_fixture import (
    ModelGoldenChainFixture,
)
from omnibase_core.runtime.golden_chain import (
    EnumGoldenChainFailureClass,
    GoldenChainReplayError,
    RecordedReplayInferenceTransport,
    canonical_request_hash,
    load_fixture,
    record_fixture,
    require_record_mode_disabled,
)

pytestmark = pytest.mark.unit

_ENDPOINT = "https://api.z.ai/v1/chat/completions"
_MODEL = "glm-5.2"


def _payload(model: str = _MODEL, max_tokens: int = 4096) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a code reviewer."},
            {"role": "user", "content": "Review this diff."},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }


def _raw_response(content: str = '{"verdict":"PASS"}') -> dict[str, Any]:
    return {
        "id": "chatcmpl-recorded",
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
    }


def _fixture(
    *,
    payload: dict[str, Any] | None = None,
    content: str = '{"verdict":"PASS"}',
    model: str = _MODEL,
    endpoint: str = _ENDPOINT,
) -> ModelGoldenChainFixture:
    pay = payload or _payload(model=model)
    return ModelGoldenChainFixture.model_validate(
        {
            "fixture_version": "golden_chain_fixture.v1",
            "provenance": {
                "provider": "zai",
                "model_id": model,
                "endpoint_ref": "cloud-glm",
                "endpoint": endpoint,
                "request_hash": canonical_request_hash(pay),
                "prompt_hash": "sha256:deadbeef",
                "routing_contract_hash": "sha256:contracthash",
                "routing_overlay_hash": "none",
                "recorded_at": "2026-06-22T00:00:00+00:00",
                "fixture_version": "golden_chain_fixture.v1",
            },
            "raw_response": _raw_response(content),
        }
    )


def test_replay_returns_recorded_bytes_for_matching_route() -> None:
    transport = RecordedReplayInferenceTransport([_fixture()])
    with transport as client:
        resp = client.post(_ENDPOINT, json=_payload(), headers={}, timeout=30.0)
    resp.raise_for_status()
    assert resp.json()["choices"][0]["message"]["content"] == '{"verdict":"PASS"}'
    assert transport.calls[0]["model"] == _MODEL


# ---- THE ROUTING-FAILURE PROOF (replay is evidence, not authority) ----------
def test_wrong_model_fails_request_hash_mismatch() -> None:
    """A route that resolves the WRONG model must FAIL, not 'replay anyway'."""
    transport = RecordedReplayInferenceTransport([_fixture()])
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(
                _ENDPOINT, json=_payload(model="gpt-4o-wrong"), headers={}, timeout=30.0
            )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH


def test_wrong_max_tokens_fails_request_hash_mismatch() -> None:
    transport = RecordedReplayInferenceTransport([_fixture()])
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(
                _ENDPOINT, json=_payload(max_tokens=99), headers={}, timeout=30.0
            )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH


def test_wrong_endpoint_fails_route_not_resolved() -> None:
    transport = RecordedReplayInferenceTransport([_fixture()])
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(
                "https://wrong.example/v1/chat/completions",
                json=_payload(),
                headers={},
                timeout=30.0,
            )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED


@pytest.mark.parametrize(
    "tier", ["cheap_cloud", "cheap_frontier", "frontier_api", "local", "unknown"]
)
def test_tier_name_as_model_key_hard_rejected(tier: str) -> None:
    transport = RecordedReplayInferenceTransport([_fixture()])
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(_ENDPOINT, json=_payload(model=tier), headers={}, timeout=30.0)
    assert exc.value.failure_class is EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED


def test_empty_completion_fixture_fails_closed(tmp_path: Path) -> None:
    fx = _fixture(content="   ")
    p = tmp_path / "empty.json"
    p.write_text(json.dumps(fx.model_dump(mode="json")))
    with pytest.raises(GoldenChainReplayError) as exc:
        load_fixture(p)
    assert exc.value.failure_class is EnumGoldenChainFailureClass.EMPTY_COMPLETION


def test_malformed_fixture_fails_invalid_fixture(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text('{"fixture_version": "v1"}')  # missing provenance + raw_response
    with pytest.raises(GoldenChainReplayError) as exc:
        load_fixture(p)
    assert exc.value.failure_class is EnumGoldenChainFailureClass.INVALID_FIXTURE


def test_missing_fixture_file_fails_invalid_fixture(tmp_path: Path) -> None:
    with pytest.raises(GoldenChainReplayError) as exc:
        load_fixture(tmp_path / "nope.json")
    assert exc.value.failure_class is EnumGoldenChainFailureClass.INVALID_FIXTURE


def test_load_fixture_roundtrip(tmp_path: Path) -> None:
    fx = _fixture()
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(fx.model_dump(mode="json")))
    loaded = load_fixture(p)
    assert loaded.provenance.model_id == _MODEL
    transport = RecordedReplayInferenceTransport([loaded])
    with transport as client:
        resp = client.post(_ENDPOINT, json=_payload(), headers={}, timeout=30.0)
    assert resp.json()["usage"]["total_tokens"] == 59


# ---- record-mode authority --------------------------------------------------
def test_record_mode_disabled_passes_outside_ci() -> None:
    # Local manual run (no CI markers) with record mode on is allowed.
    require_record_mode_disabled({"OMN_RECORD_GOLDEN": "1"})


def test_record_mode_fails_closed_in_pr_ci() -> None:
    with pytest.raises(RuntimeError, match="must REPLAY fixtures only"):
        require_record_mode_disabled({"OMN_RECORD_GOLDEN": "1", "CI": "true"})


def test_record_mode_allowed_in_nightly() -> None:
    require_record_mode_disabled(
        {"OMN_RECORD_GOLDEN": "1", "CI": "true", "OMN_GOLDEN_NIGHTLY_RECORD": "1"}
    )


def test_record_fixture_blocked_in_pr_ci(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="must REPLAY fixtures only"):
        record_fixture(
            output_path=tmp_path / "x.json",
            provider="zai",
            model_id=_MODEL,
            endpoint_ref="cloud-glm",
            endpoint=_ENDPOINT,
            request_payload=_payload(),
            raw_response=_raw_response(),
            routing_contract_path=tmp_path / "missing.yaml",
            env={"OMN_RECORD_GOLDEN": "1", "GITHUB_ACTIONS": "true"},
        )


def test_record_fixture_writes_provenance_stamped_fixture(tmp_path: Path) -> None:
    contract = tmp_path / "bifrost.yaml"
    contract.write_text("backends: []\n")
    out = tmp_path / "fx.json"
    fixture = record_fixture(
        output_path=out,
        provider="zai",
        model_id=_MODEL,
        endpoint_ref="cloud-glm",
        endpoint=_ENDPOINT,
        request_payload=_payload(),
        raw_response=_raw_response(),
        routing_contract_path=contract,
        env={"OMN_RECORD_GOLDEN": "1"},  # local, no CI markers
    )
    assert out.is_file()
    assert fixture.provenance.request_hash == canonical_request_hash(_payload())
    assert fixture.provenance.routing_contract_hash.startswith("sha256:")
    assert fixture.provenance.routing_overlay_hash == "none"
    # The written fixture replays cleanly through the transport.
    loaded = load_fixture(out)
    transport = RecordedReplayInferenceTransport([loaded])
    with transport as client:
        resp = client.post(_ENDPOINT, json=_payload(), headers={}, timeout=30.0)
    assert resp.json()["choices"][0]["message"]["content"] == '{"verdict":"PASS"}'


def test_relaxed_hash_mode_still_matches_model(tmp_path: Path) -> None:
    """Relaxed-hash mode selects by endpoint+model, not blindly endpoint_matches[0]."""
    right = _fixture(model=_MODEL, content='{"verdict":"PASS"}')
    wrong = _fixture(model="some-other-model", content='{"verdict":"FAIL"}')
    transport = RecordedReplayInferenceTransport(
        [wrong, right], enforce_request_hash=False
    )
    with transport as client:
        resp = client.post(
            _ENDPOINT, json=_payload(model=_MODEL), headers={}, timeout=30.0
        )
    # Must return the fixture recorded for the live model, not the first match.
    assert resp.json()["choices"][0]["message"]["content"] == '{"verdict":"PASS"}'


def test_relaxed_hash_mode_no_model_for_endpoint_fails() -> None:
    """Relaxed mode fails REQUEST_HASH_MISMATCH when no fixture matches the model."""
    transport = RecordedReplayInferenceTransport(
        [_fixture(model="recorded-model")], enforce_request_hash=False
    )
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(
                _ENDPOINT, json=_payload(model="live-model"), headers={}, timeout=30.0
            )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH


def test_relaxed_hash_mode_missing_model_fails_closed() -> None:
    """A missing 'model' in relaxed mode cannot select a trusted fixture."""
    transport = RecordedReplayInferenceTransport(
        [_fixture()], enforce_request_hash=False
    )
    payload = _payload()
    del payload["model"]
    with pytest.raises(GoldenChainReplayError) as exc:
        with transport as client:
            client.post(_ENDPOINT, json=payload, headers={}, timeout=30.0)
    assert exc.value.failure_class is EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED


def test_recorder_requires_routing_contract_present(tmp_path: Path) -> None:
    """A missing required routing contract fails closed, not a 'none' sentinel."""
    with pytest.raises(GoldenChainReplayError) as exc:
        record_fixture(
            output_path=tmp_path / "fx.json",
            provider="zai",
            model_id=_MODEL,
            endpoint_ref="cloud-glm",
            endpoint=_ENDPOINT,
            request_payload=_payload(),
            raw_response=_raw_response(),
            routing_contract_path=tmp_path / "absent.yaml",
            env={"OMN_RECORD_GOLDEN": "1"},  # local, no CI markers
        )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED


def test_recorder_rejects_tier_name_as_concrete_model(tmp_path: Path) -> None:
    contract = tmp_path / "bifrost.yaml"
    contract.write_text("backends: []\n")
    with pytest.raises(GoldenChainReplayError) as exc:
        record_fixture(
            output_path=tmp_path / "fx.json",
            provider="zai",
            model_id="cheap_cloud",  # tier name, not concrete
            endpoint_ref="cloud-glm",
            endpoint=_ENDPOINT,
            request_payload=_payload(model="cheap_cloud"),
            raw_response=_raw_response(),
            routing_contract_path=contract,
            env={"OMN_RECORD_GOLDEN": "1"},
        )
    assert exc.value.failure_class is EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED
