# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the duplicate-config-ids check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.duplicate_config_ids_check.model_duplicate_config_ids_check_input import (
    ModelDuplicateConfigIdsCheckInput,
)
from omnibase_core.nodes.node_duplicate_config_ids_check_compute.handler import (
    NodeDuplicateConfigIdsCheckCompute,
)
from omnibase_core.nodes.node_duplicate_config_ids_check_compute.runtime_duplicate_config_ids_check import (
    main,
)

pytestmark = pytest.mark.unit

_MANIFEST = """\
registries:
  - path: reg.yaml
    list_path: entries
    id_field: id
"""


def _write(tmp_path: Path, registry: str) -> Path:
    (tmp_path / "reg.yaml").write_text(registry, encoding="utf-8")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(_MANIFEST, encoding="utf-8")
    return manifest


def test_handle_clean_registry_has_no_violations(tmp_path: Path) -> None:
    manifest = _write(tmp_path, "entries:\n  - id: a\n  - id: b\n")
    out = NodeDuplicateConfigIdsCheckCompute().handle(
        ModelDuplicateConfigIdsCheckInput(manifest_path=manifest, repo_root=tmp_path)
    )
    assert out.violations == ()


def test_handle_duplicate_id_is_reported(tmp_path: Path) -> None:
    manifest = _write(tmp_path, "entries:\n  - id: a\n  - id: a\n")
    out = NodeDuplicateConfigIdsCheckCompute().handle(
        ModelDuplicateConfigIdsCheckInput(manifest_path=manifest, repo_root=tmp_path)
    )
    assert len(out.violations) == 1
    assert out.violations[0].registry_path == "reg.yaml"


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean = _write(tmp_path, "entries:\n  - id: a\n  - id: b\n")
    assert main(["--manifest", str(clean), "--repo-root", str(tmp_path)]) == 0
    assert "No duplicate-id registry violations found." in capsys.readouterr().out
    dup = _write(tmp_path, "entries:\n  - id: a\n  - id: a\n")
    assert main(["--manifest", str(dup), "--repo-root", str(tmp_path)]) == 1
    assert "1 duplicate-id registry violation(s)." in capsys.readouterr().out
