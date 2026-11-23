# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-26513: no moved module or validation contract names the ledger file as a path to read or write.

The error-rule table contract named ``ONEX_LEDGER_PATH`` as the env binding of its ledger source
read; the work-ledger render CLI compared the md ledger file with the JSON-lines file. The first
now reads the bus and the second is retired. The two contracts that still name the ledger file
(a citation grammar and a scan exclusion glob) are guards, not paths.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.conftest import LEDGER_PATH_ENV

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "omnibase_core"
CONTRACTS = PACKAGE / "validation" / "contracts"


def test_no_ledger_file_path_in_the_error_rule_table_contract() -> None:
    text = (CONTRACTS / "error_rule_table.validation.yaml").read_text(encoding="utf-8")
    assert LEDGER_PATH_ENV not in text
    assert "sources_env" not in text


def test_no_ledger_file_path_policy_model_has_no_ledger_env_field() -> None:
    from omnibase_core.models.error_rule_table.model_error_rule_policy import (
        ModelErrorRulePolicy,
    )

    assert "sources_env" not in ModelErrorRulePolicy.model_fields


def test_no_ledger_file_path_render_cli_is_retired() -> None:
    assert importlib.util.find_spec("omnibase_core.cli.cli_work_ledger_render") is None
    runtime = (
        PACKAGE / "nodes" / "node_work_ledger_state_compute" / "runtime_work_ledger.py"
    ).read_text(encoding="utf-8")
    assert "cli_work_ledger_render" not in runtime
    assert LEDGER_PATH_ENV not in runtime


def test_no_ledger_file_path_render_subcommand_is_refused() -> None:
    from omnibase_core.nodes.node_work_ledger_state_compute.runtime_work_ledger import (
        main,
    )

    with pytest.raises(SystemExit) as refused:
        main(["render", "--check"])
    assert refused.value.code == 2


def test_no_ledger_file_path_runtime_code_names_the_variable_nowhere() -> None:
    """The census's own question: no runtime code names the ledger file's path variable."""
    named = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".yaml", ".yml"}
        and LEDGER_PATH_ENV in path.read_text(encoding="utf-8", errors="replace")
    }
    assert not named, named
