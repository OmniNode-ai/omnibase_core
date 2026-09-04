# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# api-key-env-ok: OMN-17931 — fixtures ARE intentional api_key_env declarations

"""OMN-17931 (OMN-17372 AC3, mechanical half): ``api_key_env`` is not a logical ref.

``api_key_env`` names a HOUSE environment variable. A cloud backend that carries
one resolves a platform-held provider credential from the runtime env — the
exact path OMN-17372 AC3 requires to be unreachable by construction. Before
this ticket both backend-secret-discipline twins (the fleet-enforced CLI module
``omnibase_core.validators.backend_secret_discipline`` and the COMPUTE twin
``omnibase_core.validation.validator_backend_secret_discipline``) accepted
``api_key_env`` as satisfying the logical-reference requirement, while
``omnibase_core.validation.api_key_ref_discipline`` already rejected it
(OMN-12878). These tests pin the aligned, stricter posture on BOTH twins:

* a cloud backend whose only credential declaration is ``api_key_env`` is a
  ``backend-ref`` finding that names the backend and ``api_key_env``;
* ``api_key_env`` alongside a real logical ref is the migration-debt shape and
  is ALSO a finding — the store-resolved ref is the only declaration allowed;
* a backend with ``secret_ref`` / ``api_key_ref`` / ``credential_ref`` alone is
  clean (positive control: the ratchet does not over-reject).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.validation import validator_backend_secret_discipline as node_mod
from omnibase_core.validators import backend_secret_discipline as cli_mod

pytestmark = pytest.mark.unit

_ONLY_API_KEY_ENV = (
    "backends:\n"
    "  - backend_id: cloud-openrouter\n"
    "    tier: cheap_cloud\n"
    "    api_key_env: OPENROUTER_API_KEY\n"
)
_API_KEY_ENV_BESIDE_SECRET_REF = (
    "backends:\n"
    "  - backend_id: cloud-openrouter\n"
    "    tier: cheap_cloud\n"
    "    secret_ref: llm.openrouter.api_key\n"
    "    api_key_env: OPENROUTER_API_KEY\n"
)
_SECRET_REF_ONLY = (
    "backends:\n"
    "  - backend_id: cloud-openrouter\n"
    "    tier: cheap_cloud\n"
    "    secret_ref: llm.openrouter.api_key\n"
)
_API_KEY_REF_ONLY = (
    "backends:\n"
    "  - backend_id: cloud-openrouter\n"
    "    tier: cheap_cloud\n"
    "    api_key_ref: llm.openrouter.api_key\n"
)
_CREDENTIAL_REF_ONLY = (
    "backends:\n"
    "  - backend_id: cloud-vertex-gemini\n"
    "    tier: frontier_api\n"
    "    credential_ref: llm.vertex.adc\n"
)


# ---------------------------------------------------------------------------
# CLI twin — the module the fleet-enforced hooks / CI steps invoke
# ---------------------------------------------------------------------------


def test_cli_twin_only_api_key_env_is_a_missing_logical_ref() -> None:
    findings = cli_mod.scan_backends("bifrost.yaml", yaml.safe_load(_ONLY_API_KEY_ENV))
    assert findings, "api_key_env alone must NOT satisfy the logical-ref requirement"
    messages = [f.message for f in findings]
    assert any("cloud-openrouter" in m and "api_key_env" in m for m in messages), (
        messages
    )
    assert all(f.category == "backend-ref" for f in findings)


def test_cli_twin_api_key_env_beside_secret_ref_is_migration_debt() -> None:
    findings = cli_mod.scan_backends(
        "bifrost.yaml", yaml.safe_load(_API_KEY_ENV_BESIDE_SECRET_REF)
    )
    assert findings, "api_key_env beside a real ref is the migration-debt shape"
    assert any(
        "cloud-openrouter" in f.message and "api_key_env" in f.message for f in findings
    )


@pytest.mark.parametrize(
    "text", [_SECRET_REF_ONLY, _API_KEY_REF_ONLY, _CREDENTIAL_REF_ONLY]
)
def test_cli_twin_real_logical_refs_stay_clean(text: str) -> None:
    assert cli_mod.scan_backends("bifrost.yaml", yaml.safe_load(text)) == []


def test_cli_twin_end_to_end_report_fails_on_api_key_env(tmp_path: Path) -> None:
    """The exact surface omnimarket ci.yml / the pre-commit hooks call."""
    cfg = tmp_path / "bifrost_delegation.yaml"
    cfg.write_text(_ONLY_API_KEY_ENV, encoding="utf-8")
    report = cli_mod.build_report([cfg], cwd=tmp_path)
    assert report["passed"] is False
    backend_msgs = report["backend_ref_violations"]
    assert isinstance(backend_msgs, list)
    assert any("api_key_env" in m for m in backend_msgs), backend_msgs
    assert cli_mod.main([str(cfg)]) == 1


# ---------------------------------------------------------------------------
# COMPUTE twin — node_backend_secret_discipline_compute
# ---------------------------------------------------------------------------


def test_node_twin_only_api_key_env_is_a_missing_logical_ref() -> None:
    violations = node_mod.scan_bifrost_backends(
        "bifrost.yaml", yaml.safe_load(_ONLY_API_KEY_ENV)
    )
    assert violations, "api_key_env alone must NOT satisfy the logical-ref requirement"
    assert any(
        "cloud-openrouter" in v.message and "api_key_env" in v.message
        for v in violations
    )


def test_node_twin_api_key_env_beside_secret_ref_is_migration_debt() -> None:
    violations = node_mod.scan_bifrost_backends(
        "bifrost.yaml", yaml.safe_load(_API_KEY_ENV_BESIDE_SECRET_REF)
    )
    assert violations
    assert any(
        "cloud-openrouter" in v.message and "api_key_env" in v.message
        for v in violations
    )


@pytest.mark.parametrize(
    "text", [_SECRET_REF_ONLY, _API_KEY_REF_ONLY, _CREDENTIAL_REF_ONLY]
)
def test_node_twin_real_logical_refs_stay_clean(text: str) -> None:
    assert node_mod.scan_bifrost_backends("bifrost.yaml", yaml.safe_load(text)) == []


def test_node_twin_report_fails_on_api_key_env() -> None:
    report = node_mod.build_report_from_files({"bifrost.yaml": _ONLY_API_KEY_ENV})
    assert report.passed is False
    assert any("api_key_env" in v.message for v in report.backend_ref_violations)


def test_twins_agree_with_api_key_ref_discipline() -> None:
    """The two core validators must not disagree about api_key_env (OMN-12878)."""
    from omnibase_core.validation.api_key_ref_discipline.handler import (
        scan_bifrost_yaml,
    )

    guard = scan_bifrost_yaml("bifrost.yaml", _ONLY_API_KEY_ENV)
    assert guard, "positive control: api_key_ref_discipline rejects api_key_env"
    assert cli_mod.scan_backends("bifrost.yaml", yaml.safe_load(_ONLY_API_KEY_ENV))
    assert node_mod.scan_bifrost_backends(
        "bifrost.yaml", yaml.safe_load(_ONLY_API_KEY_ENV)
    )
