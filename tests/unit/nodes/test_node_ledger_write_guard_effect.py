# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Exercise the ledger guard through its published default handler."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_compliance import compliance_group
from omnibase_core.enums.enum_ledger_write_target import EnumLedgerWriteTarget
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_request import (
    ModelLedgerWriteGuardRequest,
)
from omnibase_core.nodes import node_ledger_write_guard_effect

pytestmark = pytest.mark.unit

NODE_ROOT = Path(node_ledger_write_guard_effect.__file__).parent


@pytest.mark.parametrize(
    ("kind", "target", "refused"),
    [
        (EnumLedgerWriteTarget.FILE, "/var/lib/onex/ledger.md", True),
        (
            EnumLedgerWriteTarget.TOPIC,
            "onex.evt.omnimarket.work-ledger-row-appended.v1",
            True,
        ),
        (EnumLedgerWriteTarget.DSN, "postgresql://u@db.internal.example/db", True),
        (EnumLedgerWriteTarget.TOPIC, "onex.evt.test.scratch.v1", False),
        (EnumLedgerWriteTarget.DSN, "postgresql://u@localhost/db", False),
    ],
)
def test_default_handler_classifies_targets(
    kind: EnumLedgerWriteTarget, target: str, refused: bool
) -> None:
    contract = yaml.safe_load((NODE_ROOT / "contract.yaml").read_text())
    module_name, class_name = contract["handler_routing"]["default_handler"].split(":")
    module = import_module(f"{node_ledger_write_guard_effect.__name__}.{module_name}")
    handler = getattr(module, class_name)()
    decision = handler.handle(
        ModelLedgerWriteGuardRequest(target_kind=kind, target=target)
    )
    assert decision.refused is refused
    assert (decision.signal is not None) is refused


def test_node_passes_contract_compliance(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        compliance_group,
        [
            "check",
            "--repo-root",
            str(NODE_ROOT),
            "--output",
            str(tmp_path / "report.yaml"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "PASS node_ledger_write_guard_effect [8/8 checks]" in result.output
