# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelWorkflowCoordinator."""

from uuid import uuid4

import pytest

from omnibase_core.models.container.model_workflow_coordinator import (
    ModelWorkflowCoordinator,
)
from omnibase_core.models.container.model_workflow_factory import ModelWorkflowFactory


@pytest.mark.unit
class TestModelWorkflowCoordinator:
    """Tests for ModelWorkflowCoordinator."""

    def test_initialization(self):
        """Test coordinator initialization."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        assert coordinator is not None
        assert coordinator.factory is factory
        assert coordinator.active_workflows == {}

    def test_initialization_stores_factory(self):
        """Test coordinator stores factory reference."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        assert coordinator.factory is factory
        workflows = coordinator.factory.list_available_workflows()
        assert len(workflows) > 0

    def test_active_workflows_initialized_empty(self):
        """Test active workflows dict is initialized empty."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        assert isinstance(coordinator.active_workflows, dict)
        assert len(coordinator.active_workflows) == 0

    def test_coordinator_with_different_factories(self):
        """Test coordinator works with different factory instances."""
        factory1 = ModelWorkflowFactory()
        factory2 = ModelWorkflowFactory()

        coordinator1 = ModelWorkflowCoordinator(factory1)
        coordinator2 = ModelWorkflowCoordinator(factory2)

        assert coordinator1.factory is factory1
        assert coordinator2.factory is factory2
        assert coordinator1.factory is not coordinator2.factory

    @pytest.mark.asyncio
    async def test_execute_workflow_basic(self):
        """Test basic workflow execution."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        workflow_id = str(uuid4())
        result = await coordinator.execute_workflow(
            workflow_id,
            "simple_sequential",
            {"data": "test"},
        )
        # Returns None as factory creates None

    @pytest.mark.asyncio
    async def test_execute_workflow_with_config(self):
        """Test workflow execution with config."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        workflow_id = str(uuid4())
        config = {"timeout": 30, "retry": True}
        result = await coordinator.execute_workflow(
            workflow_id,
            "retry_with_backoff",
            {"data": "test"},
            config,
        )

    @pytest.mark.asyncio
    async def test_execute_workflow_various_types(self):
        """Test executing different workflow types."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        workflow_types = factory.list_available_workflows()

        for workflow_type in workflow_types:
            workflow_id = str(uuid4())
            await coordinator.execute_workflow(
                workflow_id,
                workflow_type,
                {"data": "test"},
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_with_input_data(self):
        """Test workflow execution with various input data."""
        factory = ModelWorkflowFactory()
        coordinator = ModelWorkflowCoordinator(factory)

        # Simple data
        await coordinator.execute_workflow(
            "wf-1",
            "simple_sequential",
            "simple string",
        )

        # Complex data
        await coordinator.execute_workflow(
            "wf-2",
            "data_pipeline",
            {"items": [1, 2, 3], "metadata": {"source": "test"}},
        )

        # List data
        await coordinator.execute_workflow(
            "wf-3",
            "parallel_execution",
            [1, 2, 3, 4, 5],
        )
