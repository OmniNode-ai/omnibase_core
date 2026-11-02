# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``emits`` declaration of validator-requirements.yaml entries (OMN-22003, AC1/AC2).

Every spec entry declares ``emits`` (required, or exempt with a reason), an entry that
omits it is rejected on load, and the consumer's emits judgment reports a wired
pre-commit entry that is not a core-format runtime writing through the report writer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_validator_requirement_emits import (
    EnumValidatorRequirementEmits,
)
from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_validator_requirement_entry import (
    ModelValidatorRequirementEntry,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.runtime_requirements_consumer_check import (
    main,
)
from omnibase_core.validation.validator_requirements_consumer import (
    ValidatorRequirementsConsumer,
)

pytestmark = pytest.mark.unit

_SPEC = (
    Path(__file__).resolve().parents[3]
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)
_TOOLS = {"bandit-security", "mypy-type-check", "ruff-format-check", "detect-secrets"}


def _entry(**override: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "description": "x",
        "central_source": "x",
        "pre_commit": "required",
        "ci_workflow": "optional",
        "required_check_on_main": None,
        "silent_skip_allowed": False,
        "pre_commit_hook_ids": ["my-validator"],
        "applies_to_repos": "all",
        "emits": "required",
    }
    base.update(override)
    return {
        k: v for k, v in base.items() if v is not None or k == "required_check_on_main"
    }


def _spec_file(tmp_path: Path, entry: dict[str, Any], *, rules: bool = True) -> Path:
    document: dict[str, Any] = {
        "schema_version": {"major": 1, "minor": 5, "patch": 0},
        "known_repos": [],
        "required_validators": {"my-validator": entry},
    }
    if rules:
        document["emits_check"] = {
            "module_pattern": r"-m\s+([A-Za-z_][A-Za-z0-9_.]*)",
            "core_package": "omnibase_core",
            "writer_marker": "NodeValidationReportWriteEffect",
        }
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(document))
    return path


def _repo(tmp_path: Path, entries: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    hooks = [
        {"id": hook_id, "name": hook_id, "entry": entry, "language": "system"}
        for hook_id, entry in entries.items()
    ]
    (root / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]})
    )
    return root


def test_validator_requirements_emits_is_required_on_load() -> None:
    entry = _entry()
    del entry["emits"]
    with pytest.raises(ValidationError, match="emits"):
        ModelValidatorRequirementEntry.model_validate(entry)


def test_validator_requirements_emits_exempt_needs_a_reason() -> None:
    with pytest.raises(ValidationError, match="emits_exempt_reason"):
        ModelValidatorRequirementEntry.model_validate(_entry(emits="exempt"))
    exempt = ModelValidatorRequirementEntry.model_validate(
        _entry(emits="exempt", emits_exempt_reason="third-party tool")
    )
    assert exempt.emits is EnumValidatorRequirementEmits.EXEMPT


def test_validator_requirements_emits_required_forbids_a_reason() -> None:
    with pytest.raises(ValidationError, match="emits_exempt_reason"):
        ModelValidatorRequirementEntry.model_validate(
            _entry(emits="required", emits_exempt_reason="because")
        )


def test_validator_requirements_emits_rejects_an_unknown_value() -> None:
    with pytest.raises(ValidationError, match="emits"):
        ModelValidatorRequirementEntry.model_validate(_entry(emits="maybe"))


def test_validator_requirements_emits_every_spec_entry_declares_it() -> None:
    raw = yaml.safe_load(_SPEC.read_text())["required_validators"]
    assert raw, "the spec holds no validators"
    undeclared = [name for name, entry in raw.items() if "emits" not in entry]
    assert undeclared == []
    consumer = ValidatorRequirementsConsumer.from_canonical()
    assert set(consumer.validators) == set(raw)


def test_validator_requirements_emits_exempt_is_only_for_third_party_tools() -> None:
    consumer = ValidatorRequirementsConsumer.from_canonical()
    exempt = {
        name
        for name, entry in consumer.validators.items()
        if entry.emits is EnumValidatorRequirementEmits.EXEMPT
    }
    assert exempt == _TOOLS


def test_validator_requirements_emits_stripped_from_one_spec_entry_fails_load(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load(_SPEC.read_text())
    victim = next(iter(document["required_validators"]))
    del document["required_validators"][victim]["emits"]
    stripped = tmp_path / "stripped.yaml"
    stripped.write_text(yaml.safe_dump(document))
    with pytest.raises(ValueError, match=victim):
        ValidatorRequirementsConsumer.from_spec_path(stripped)


def test_validator_requirements_emits_check_block_is_spec_data() -> None:
    document = yaml.safe_load(_SPEC.read_text())
    assert set(document["emits_check"]) == {
        "module_pattern",
        "core_package",
        "writer_marker",
    }
    assert document["schema_version"] == {"major": 1, "minor": 5, "patch": 0}


def test_validator_requirements_emits_unrequested_check_reports_nothing(
    tmp_path: Path,
) -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(
        _spec_file(tmp_path, _entry())
    )
    root = _repo(tmp_path, {"my-validator": "bash run.sh"})
    assert consumer.scan_repo(repo_name="r", repo_root=root) == []


def test_validator_requirements_emits_bare_script_is_reported_with_its_hook_id(
    tmp_path: Path,
) -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(
        _spec_file(tmp_path, _entry())
    )
    root = _repo(tmp_path, {"my-validator": "bash run.sh"})
    gaps = consumer.scan_repo(repo_name="r", repo_root=root, check_emits=True)
    assert [(g.kind, g.hook_id) for g in gaps] == [
        (EnumValidatorRequirementGapKind.NON_EMITTING_ENTRY, "my-validator")
    ]


def test_validator_requirements_emits_exempt_entry_is_not_judged(
    tmp_path: Path,
) -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(
        _spec_file(
            tmp_path, _entry(emits="exempt", emits_exempt_reason="third-party tool")
        )
    )
    root = _repo(tmp_path, {"my-validator": "bash run.sh"})
    assert consumer.scan_repo(repo_name="r", repo_root=root, check_emits=True) == []


def test_validator_requirements_emits_check_without_spec_rules_fails_loud(
    tmp_path: Path,
) -> None:
    consumer = ValidatorRequirementsConsumer.from_spec_path(
        _spec_file(tmp_path, _entry(), rules=False)
    )
    root = _repo(tmp_path, {"my-validator": "bash run.sh"})
    with pytest.raises(ModelOnexError, match="emits_check"):
        consumer.scan_repo(repo_name="r", repo_root=root, check_emits=True)


def test_validator_requirements_emits_canary_new_bare_script_hook_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = _spec_file(tmp_path, _entry())
    module = tmp_path / "repo" / "src" / "omnibase_core" / "canary"
    module.mkdir(parents=True)
    (module / "runtime_ok.py").write_text("NodeValidationReportWriteEffect = 1\n")
    root = _repo(
        tmp_path, {"my-validator": "uv run python -m omnibase_core.canary.runtime_ok"}
    )
    argv = ["--repo", "r", "--repo-root", str(root), "--spec", str(spec), "--emits"]
    assert main(argv) == 0
    capsys.readouterr()

    _repo(
        tmp_path,
        {
            "my-validator": "uv run python -m omnibase_core.canary.runtime_ok",
            "my-validator-bare": "uv run python scripts/check_my_validator.py",
        },
    )
    assert main(argv) == 2
    assert "NON_EMITTING_ENTRY" in capsys.readouterr().err
