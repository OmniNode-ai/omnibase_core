# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An unavailable scan root reads as unavailable, never as an empty inventory (OMN-23114).

The loader scans ``<root>/*/contract.yaml``. A root that is missing or is not a directory used to
produce the same result as a directory holding no node contracts, so a mistyped path read as "no
effect nodes without a default". An unavailable root now carries its reason through the loader,
the request and the report.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_effect_backends_load_request import (
    ModelEffectBackendsLoadRequest,
)
from omnibase_core.models.validation.model_effect_backends_request import (
    ModelEffectBackendsRequest,
)
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends import (
    HandlerEffectBackends,
)
from omnibase_core.nodes.node_effect_backends_check_compute.handler_effect_backends_loader import (
    HandlerEffectBackendsLoader,
)

pytestmark = pytest.mark.unit


def _scan(root: Path):
    loaded = HandlerEffectBackendsLoader().handle(
        ModelEffectBackendsLoadRequest(root=str(root))
    )
    report = HandlerEffectBackends().handle(
        ModelEffectBackendsRequest(
            contracts=loaded.documents,
            unreadable=loaded.unreadable,
            root_unavailable=loaded.root_unavailable,
        )
    )
    return loaded, report


def test_missing_root_is_unavailable_not_empty(tmp_path: Path) -> None:
    loaded, report = _scan(tmp_path / "no_such_directory")
    assert loaded.root_unavailable != ""
    assert report.inventory_available is False
    assert report.root_unavailable == loaded.root_unavailable
    assert report.effects_total == 0


def test_root_that_is_a_file_is_unavailable(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "plain_file"
    not_a_dir.write_text("x")
    loaded, report = _scan(not_a_dir)
    assert loaded.root_unavailable != ""
    assert report.inventory_available is False


def test_existing_empty_root_is_an_available_empty_inventory(tmp_path: Path) -> None:
    loaded, report = _scan(tmp_path)
    assert loaded.root_unavailable == ""
    assert report.inventory_available is True
    assert report.root_unavailable == ""
    assert report.effects_total == 0
