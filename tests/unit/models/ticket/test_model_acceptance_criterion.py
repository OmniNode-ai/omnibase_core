# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelAcceptanceCriterion."""

import pytest


@pytest.mark.unit
def test_criterion_required_fields() -> None:
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )

    c = ModelAcceptanceCriterion(id="ac_1", statement="reducer raises ValueError")
    assert c.id == "ac_1"
    assert c.statement == "reducer raises ValueError"


@pytest.mark.unit
def test_criterion_is_frozen() -> None:
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )

    c = ModelAcceptanceCriterion(id="ac_1", statement="s")
    with pytest.raises(Exception):
        c.id = "ac_2"  # type: ignore[misc]


@pytest.mark.unit
def test_criterion_id_must_be_nonempty() -> None:
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )

    with pytest.raises(Exception):
        ModelAcceptanceCriterion(id="", statement="s")


@pytest.mark.unit
def test_criterion_statement_must_be_nonempty() -> None:
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )

    with pytest.raises(Exception):
        ModelAcceptanceCriterion(id="ac_1", statement="")


@pytest.mark.unit
def test_criterion_whitespace_only_fails() -> None:
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )

    with pytest.raises(Exception):
        ModelAcceptanceCriterion(id="   ", statement="s")
