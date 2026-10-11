# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The dead-endpoint denylist comes from the operator's private vocabulary (OMN-20939).

The shipped policy carries shape rules only. A deployment's dead endpoints are
read from ``vocabularies/hardcoded_model_config_lab_denylist.yaml`` under the
workspace config root when that file exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)
from omnibase_core.validation.hardcoded_model_config.handler import scan

# Synthetic endpoints in the RFC 5737 documentation range, never a real one.
DEAD_ENDPOINT = "192.0.2.77:8101"
OTHER_DEAD_ENDPOINT = "198.51.100.5:8099"


def _write_vocabulary(root: Path, body: str) -> None:
    target = root / "vocabularies" / "hardcoded_model_config_lab_denylist.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(body, encoding="utf-8")


@pytest.fixture
def no_ambient_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ONEX_WORKSPACE_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("OMNI_HOME", raising=False)


@pytest.mark.unit
def test_shipped_policy_names_no_lab_endpoint(no_ambient_root: None) -> None:
    policy = runtime.load_policy()
    assert not any(":8101" in v or ":8099" in v for v in policy.retired_values)
    assert "model_id_pattern" in policy.model_dump()


@pytest.mark.unit
def test_private_vocabulary_adds_its_dead_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_vocabulary(
        tmp_path,
        f'schema_version: 1\nretired_values:\n  - "{DEAD_ENDPOINT}"\n'
        f'  - "{OTHER_DEAD_ENDPOINT}"\n',
    )
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(tmp_path))
    policy = runtime.load_policy()
    assert DEAD_ENDPOINT in policy.retired_values
    assert OTHER_DEAD_ENDPOINT in policy.retired_values
    findings = scan("src/pkg/notes.py", f"# was {DEAD_ENDPOINT}\n", policy)
    assert [f.family for f in findings] == ["R"]


@pytest.mark.unit
def test_without_the_vocabulary_the_same_line_is_not_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(tmp_path))
    policy = runtime.load_policy()
    assert scan("src/pkg/notes.py", f"# was {DEAD_ENDPOINT}\n", policy) == []


@pytest.mark.unit
def test_a_malformed_vocabulary_stops_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_vocabulary(tmp_path, "schema_version: 1\nretired_values: not-a-list\n")
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(tmp_path))
    with pytest.raises(runtime._InputError, match="lab denylist is invalid"):
        runtime.load_policy()
