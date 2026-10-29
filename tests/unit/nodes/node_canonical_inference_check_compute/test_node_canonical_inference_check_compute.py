# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the canonical-inference check node (OMN-21520)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.canonical_inference_check.model_canonical_inference_check_input import (
    ModelCanonicalInferenceCheckInput,
)
from omnibase_core.models.validation.model_canonical_inference_violation import (
    ModelCanonicalInferenceViolation,
)
from omnibase_core.nodes.node_canonical_inference_check_compute.handler import (
    NodeCanonicalInferenceCheckCompute,
)
from omnibase_core.nodes.node_canonical_inference_check_compute.runtime_canonical_inference_check import (
    main,
)
from omnibase_core.validation.validator_canonical_inference import make_fingerprint

pytestmark = pytest.mark.unit

_SNIPPET = 'subprocess.run(["codex", "exec"])'


def _violation() -> ModelCanonicalInferenceViolation:
    return ModelCanonicalInferenceViolation(
        repo="r",
        path="mod.py",
        line=1,
        rule="model-cli-shellout",
        snippet=_SNIPPET,
        fingerprint=make_fingerprint("r", "mod.py", _SNIPPET),
    )


def _baseline(tmp_path: Path, fingerprints: list[str]) -> Path:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps({"violations": [{"fingerprint": fp} for fp in fingerprints]}),
        encoding="utf-8",
    )
    return path


def test_handle_new_violation_is_not_grandfathered() -> None:
    out = NodeCanonicalInferenceCheckCompute().handle(
        ModelCanonicalInferenceCheckInput(violations=(_violation(),))
    )
    assert out.new == (_violation(),)
    assert out.grandfathered == ()


def test_handle_baselined_violation_is_grandfathered() -> None:
    violation = _violation()
    out = NodeCanonicalInferenceCheckCompute().handle(
        ModelCanonicalInferenceCheckInput(
            violations=(violation,),
            baseline_fingerprints=frozenset({violation.fingerprint}),
        )
    )
    assert out.new == ()
    assert out.grandfathered == (violation,)


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "mod.py"
    source.write_text(_SNIPPET + "\n", encoding="utf-8")
    common = [str(source), "--repo", "r", "--repo-root", str(tmp_path)]

    assert main([*common, "--baseline", str(_baseline(tmp_path, []))]) == 1
    assert "CANONICAL-INFERENCE GATE FAILED: 1 NEW violation(s)" in (
        capsys.readouterr().err
    )

    fingerprint = make_fingerprint("r", "mod.py", _SNIPPET)
    assert main([*common, "--baseline", str(_baseline(tmp_path, [fingerprint]))]) == 0
    assert (
        "CANONICAL-INFERENCE GATE PASSED: 0 new violations (1 grandfathered)."
        in capsys.readouterr().out
    )
