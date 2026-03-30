# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelTaskContract and ModelMechanicalCheck."""

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_check_type import EnumCheckType
from omnibase_core.models.task.model_mechanical_check import ModelMechanicalCheck
from omnibase_core.models.task.model_task_contract import ModelTaskContract


@pytest.mark.unit
def test_task_contract_creation() -> None:
    now = datetime.now(tz=UTC)
    contract = ModelTaskContract(
        task_id="task-1",
        parent_ticket="OMN-7001",
        repo="omnibase_infra",
        branch="jonah/omn-7001-feature",
        generated_at=now,
        requirements=["Implement handler for new node type"],
        definition_of_done=[
            ModelMechanicalCheck(
                criterion="Unit tests pass",
                check="uv run pytest tests/unit/ -m unit",
                check_type="command_exit_0",
            )
        ],
    )
    assert contract.task_id == "task-1"
    assert contract.parent_ticket == "OMN-7001"
    assert len(contract.definition_of_done) == 1
    assert contract.definition_of_done[0].check_type == EnumCheckType.COMMAND_EXIT_0
    assert contract.generated_at == now
    assert contract.schema_version == "1.0.0"


@pytest.mark.unit
def test_task_contract_is_frozen() -> None:
    contract = ModelTaskContract(
        task_id="task-1",
        generated_at=datetime.now(tz=UTC),
        requirements=["test"],
        definition_of_done=[],
    )
    with pytest.raises(Exception):  # ValidationError for frozen model
        contract.task_id = "modified"  # type: ignore[misc]


@pytest.mark.unit
def test_task_contract_yaml_roundtrip() -> None:
    now = datetime.now(tz=UTC)
    contract = ModelTaskContract(
        task_id="task-2",
        parent_ticket="OMN-7002",
        repo="omniclaude",
        generated_at=now,
        requirements=["Add hook"],
        definition_of_done=[
            ModelMechanicalCheck(
                criterion="Pre-commit passes",
                check="pre-commit run --all-files",
                check_type="command_exit_0",
            )
        ],
    )
    yaml_str = contract.to_yaml()
    loaded = ModelTaskContract.from_yaml(yaml_str)
    assert loaded.task_id == contract.task_id
    assert loaded.parent_ticket == contract.parent_ticket
    assert len(loaded.definition_of_done) == 1
    assert loaded.definition_of_done[0].criterion == "Pre-commit passes"
    assert loaded.generated_at == contract.generated_at
