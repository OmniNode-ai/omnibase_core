# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Four end-to-end value-kind fixtures and a clean control (OMN-21503)."""

from pathlib import Path

import pytest

from omnibase_core.validation.hardcoded_model_config.handler import scan
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    load_policy,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validators.contract_config_compliance import validate_file

pytestmark = pytest.mark.unit


def test_four_value_kinds_are_refused(tmp_path: Path) -> None:
    policy = load_policy().model_copy(
        update={"lab_host_names": ("fixture-lab.internal",)}
    )
    fixtures = {
        "stamp": ('VALUE = "ruling 2026-10-28T12:34:56Z"\n', "S"),
        "model": ('MODEL = "' + "gpt-" + '4"\n', "M"),
        "host": ('HOST = "fixture-lab.internal"\n', "D"),
        "threshold": ("REQUEST_TIMEOUT = 30\n", "hardcoded_threshold"),
    }
    for name, (text, kind) in fixtures.items():
        path = tmp_path / f"{name}.py"
        path.write_text(text)
        if kind == "hardcoded_threshold":
            assert [f.rule for f in validate_file(path, frozenset({kind}))] == [kind]
        else:
            assert [
                f.family for f in scan(f"src/{name}.py", path.read_text(), policy)
            ] == [kind]
    clean = tmp_path / "clean.py"
    clean.write_text('VALUE = "from contract"\n')
    assert scan("src/clean.py", clean.read_text(), policy) == []
    assert validate_file(clean) == []
    assert ValidatorHardcodedTopics().validate_file(clean).is_valid
