# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelTaskDispatch and ModelTaskTree."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.audit.model_task_dispatch import ModelTaskDispatch
from omnibase_core.models.audit.model_task_tree import ModelTaskTree


@pytest.mark.unit
class TestModelTaskDispatch:
    """Tests for ModelTaskDispatch model."""

    def test_minimal_construction(self) -> None:
        dispatch = ModelTaskDispatch(
            agent_type="onex:general-purpose",
        )
        assert isinstance(dispatch.task_id, UUID)
        assert dispatch.agent_type == "onex:general-purpose"
        assert dispatch.parent_task_id is None
        assert dispatch.tool_scope == []
        assert dispatch.context_budget_tokens is None
        assert dispatch.session_id is None
        assert dispatch.correlation_id is None
        assert dispatch.description is None
        assert isinstance(dispatch.dispatched_at, datetime)

    def test_full_construction(self) -> None:
        task_uuid = uuid4()
        parent_uuid = uuid4()
        session_uuid = uuid4()
        corr_uuid = uuid4()
        ts = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
        dispatch = ModelTaskDispatch(
            task_id=task_uuid,
            parent_task_id=parent_uuid,
            agent_type="onex:general-purpose",
            tool_scope=["Bash", "Read", "Write"],
            context_budget_tokens=50000,
            session_id=session_uuid,
            correlation_id=corr_uuid,
            dispatched_at=ts,
            description="Implement OMN-5231",
        )
        assert dispatch.task_id == task_uuid
        assert dispatch.parent_task_id == parent_uuid
        assert dispatch.tool_scope == ["Bash", "Read", "Write"]
        assert dispatch.context_budget_tokens == 50000
        assert dispatch.session_id == session_uuid
        assert dispatch.correlation_id == corr_uuid
        assert dispatch.dispatched_at == ts
        assert dispatch.description == "Implement OMN-5231"

    def test_frozen_immutability(self) -> None:
        dispatch = ModelTaskDispatch(
            agent_type="onex:general-purpose",
        )
        with pytest.raises(ValidationError):
            dispatch.agent_type = "changed"  # type: ignore[misc]

    def test_context_budget_minimum(self) -> None:
        with pytest.raises(ValidationError):
            ModelTaskDispatch(
                agent_type="onex:general-purpose",
                context_budget_tokens=0,
            )


@pytest.mark.unit
class TestModelTaskTree:
    """Tests for ModelTaskTree model."""

    def _make_dispatch(
        self,
        task_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        agent_type: str = "onex:general-purpose",
    ) -> ModelTaskDispatch:
        return ModelTaskDispatch(
            task_id=task_id or uuid4(),
            parent_task_id=parent_task_id,
            agent_type=agent_type,
        )

    def test_empty_tree(self) -> None:
        session_uuid = uuid4()
        tree = ModelTaskTree(session_id=session_uuid)
        assert tree.session_id == session_uuid
        assert tree.dispatches == []
        assert tree.root_dispatches == []
        assert tree.depth == 0
        assert tree.total_dispatches == 0

    def test_flat_tree(self) -> None:
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[
                self._make_dispatch(),
                self._make_dispatch(),
                self._make_dispatch(),
            ],
        )
        assert tree.total_dispatches == 3
        assert len(tree.root_dispatches) == 3
        assert tree.depth == 1

    def test_nested_tree(self) -> None:
        root_id = uuid4()
        child1_id = uuid4()
        child2_id = uuid4()
        grandchild_id = uuid4()
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[
                self._make_dispatch(task_id=root_id),
                self._make_dispatch(task_id=child1_id, parent_task_id=root_id),
                self._make_dispatch(task_id=child2_id, parent_task_id=root_id),
                self._make_dispatch(task_id=grandchild_id, parent_task_id=child1_id),
            ],
        )
        assert tree.total_dispatches == 4
        assert len(tree.root_dispatches) == 1
        assert tree.root_dispatches[0].task_id == root_id
        assert tree.depth == 3

    def test_get_children(self) -> None:
        root_id = uuid4()
        child1_id = uuid4()
        child2_id = uuid4()
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[
                self._make_dispatch(task_id=root_id),
                self._make_dispatch(task_id=child1_id, parent_task_id=root_id),
                self._make_dispatch(task_id=child2_id, parent_task_id=root_id),
            ],
        )
        children = tree.get_children(root_id)
        assert len(children) == 2
        child_ids = {c.task_id for c in children}
        assert child_ids == {child1_id, child2_id}

    def test_get_children_no_match(self) -> None:
        root_id = uuid4()
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[self._make_dispatch(task_id=root_id)],
        )
        assert tree.get_children(root_id) == []

    def test_get_dispatch(self) -> None:
        t1_id = uuid4()
        t2_id = uuid4()
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[
                self._make_dispatch(task_id=t1_id),
                self._make_dispatch(task_id=t2_id),
            ],
        )
        result = tree.get_dispatch(t2_id)
        assert result is not None
        assert result.task_id == t2_id

    def test_get_dispatch_not_found(self) -> None:
        tree = ModelTaskTree(
            session_id=uuid4(),
            dispatches=[self._make_dispatch()],
        )
        assert tree.get_dispatch(uuid4()) is None

    def test_re_export_from_audit_init(self) -> None:
        """Verify re-export from audit __init__.py."""
        from omnibase_core.models.audit import ModelTaskDispatch as D
        from omnibase_core.models.audit import ModelTaskTree as T

        assert D is ModelTaskDispatch
        assert T is ModelTaskTree
