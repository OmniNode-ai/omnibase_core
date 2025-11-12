"""
Comprehensive unit tests for NodeBase class.

Tests cover:
- NodeBase initialization and lifecycle
- Contract loading and validation
- Tool resolution and instantiation
- Async/sync execution interfaces
- Reducer pattern implementation
- Properties and state management
- Event emission and error handling
- Edge cases and error scenarios
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
import yaml

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.infrastructure.node_base import NodeBase
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_protocol_action import ModelAction
from omnibase_core.models.infrastructure.model_state import ModelState
from omnibase_core.models.primitives.model_semver import ModelSemVer

# ===== TEST FIXTURES =====


@pytest.fixture
def mock_contract_content():
    """Create a mock contract content object."""
    contract = Mock()
    contract.node_name = "test_node"
    contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
    contract.dependencies = []

    # Mock tool specification
    tool_spec = Mock()
    tool_spec.main_tool_class = "tests.unit.infrastructure.test_node_base.MockTool"
    tool_spec.business_logic_pattern = "test_pattern"
    contract.tool_specification = tool_spec

    return contract


@pytest.fixture
def valid_contract_file(tmp_path, mock_contract_content):
    """Create a valid test contract YAML file."""
    contract_path = tmp_path / "test_contract.yaml"
    contract_data = {
        "node_name": "test_node",
        "contract_version": "1.0.0",
        "tool_specification": {
            "main_tool_class": "tests.unit.infrastructure.test_node_base.MockTool",
            "business_logic_pattern": "test_pattern",
        },
        "dependencies": [],
    }

    with open(contract_path, "w") as f:
        yaml.dump(contract_data, f)

    return contract_path


@pytest.fixture
def mock_container():
    """Create a mock ONEX container."""
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

    return ModelONEXContainer()


# ===== MOCK TOOL CLASSES =====


class MockTool:
    """Mock tool class for testing."""

    def __init__(self, container=None):
        """Initialize mock tool."""
        self.container = container
        self.process_called = False
        self.process_async_called = False

    async def process_async(self, input_state: Any) -> Any:
        """Mock async process method."""
        self.process_async_called = True
        return {"result": "async_success"}

    def process(self, input_state: Any) -> Any:
        """Mock sync process method."""
        self.process_called = True
        return {"result": "sync_success"}


class MockToolWithRun:
    """Mock tool class with run method."""

    def __init__(self, container=None):
        """Initialize mock tool."""
        self.container = container

    def run(self, input_state: Any) -> Any:
        """Mock run method."""
        return {"result": "run_success"}


class MockToolNoMethods:
    """Mock tool class with no process methods."""

    def __init__(self, container=None):
        """Initialize mock tool."""
        self.container = container


# ===== INITIALIZATION TESTS =====


class TestNodeBaseInitialization:
    """Test NodeBase initialization and setup."""

    def test_should_initialize_with_valid_contract_path(self, tmp_path, mock_container):
        """Test NodeBase creation with valid contract path."""
        contract_path = tmp_path / "test_contract.yaml"
        contract_data = {
            "node_name": "test_node",
            "contract_version": "1.0.0",
            "tool_specification": {
                "main_tool_class": "tests.unit.infrastructure.test_node_base.MockTool",
                "business_logic_pattern": "test_pattern",
            },
            "dependencies": [],
        }

        with open(contract_path, "w") as f:
            yaml.dump(contract_data, f)

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            assert node is not None
            assert node.node_id is not None
            assert node.workflow_id is not None
            assert node.session_id is not None
            assert node.correlation_id is not None

    def test_should_initialize_with_provided_node_id(self, tmp_path, mock_container):
        """Test NodeBase with explicitly provided node_id."""
        contract_path = tmp_path / "test_contract.yaml"
        contract_data = {
            "node_name": "test_node",
            "contract_version": "1.0.0",
            "tool_specification": {
                "main_tool_class": "tests.unit.infrastructure.test_node_base.MockTool",
                "business_logic_pattern": "test_pattern",
            },
            "dependencies": [],
        }

        with open(contract_path, "w") as f:
            yaml.dump(contract_data, f)

        provided_node_id = uuid4()

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(
                contract_path=contract_path,
                node_id=provided_node_id,
                container=mock_container,
            )

            assert node.node_id == provided_node_id

    def test_should_initialize_with_workflow_and_session_ids(
        self, tmp_path, mock_container
    ):
        """Test NodeBase with provided workflow_id and session_id."""
        contract_path = tmp_path / "test_contract.yaml"
        contract_data = {
            "node_name": "test_node",
            "contract_version": "1.0.0",
            "tool_specification": {
                "main_tool_class": "tests.unit.infrastructure.test_node_base.MockTool",
                "business_logic_pattern": "test_pattern",
            },
            "dependencies": [],
        }

        with open(contract_path, "w") as f:
            yaml.dump(contract_data, f)

        workflow_id = uuid4()
        session_id = uuid4()

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(
                contract_path=contract_path,
                workflow_id=workflow_id,
                session_id=session_id,
                container=mock_container,
            )

            assert node.workflow_id == workflow_id
            assert node.session_id == session_id

    def test_should_fail_with_invalid_contract_path(self, tmp_path):
        """Test NodeBase fails with non-existent contract path."""
        contract_path = tmp_path / "nonexistent.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_contract.side_effect = FileNotFoundError(
                "Contract file not found"
            )
            mock_loader_class.return_value = mock_loader

            with pytest.raises(ModelOnexError) as exc_info:
                NodeBase(contract_path=contract_path)

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Failed to initialize NodeBase" in exc_info.value.message


# ===== TOOL RESOLUTION TESTS =====


class TestNodeBaseToolResolution:
    """Test NodeBase tool resolution and instantiation."""

    def test_should_resolve_valid_tool_class(self, tmp_path, mock_container):
        """Test resolving and instantiating a valid tool class."""
        contract_path = tmp_path / "test_contract.yaml"
        contract_data = {
            "node_name": "test_node",
            "contract_version": "1.0.0",
            "tool_specification": {
                "main_tool_class": "tests.unit.infrastructure.test_node_base.MockTool",
                "business_logic_pattern": "test_pattern",
            },
            "dependencies": [],
        }

        with open(contract_path, "w") as f:
            yaml.dump(contract_data, f)

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            assert node.main_tool is not None
            assert isinstance(node.main_tool, MockTool)
            assert node.main_tool.container == mock_container

    def test_should_fail_with_invalid_tool_class_format(self, tmp_path, mock_container):
        """Test that invalid tool class format raises error."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = "InvalidFormat"  # No module path
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            with pytest.raises(ModelOnexError) as exc_info:
                NodeBase(contract_path=contract_path, container=mock_container)

            # The validation error is wrapped in OPERATION_FAILED during initialization
            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Invalid main_tool_class format" in exc_info.value.message

    def test_should_fail_with_nonexistent_module(self, tmp_path, mock_container):
        """Test that nonexistent module raises error."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = "nonexistent.module.ToolClass"
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            with pytest.raises(ModelOnexError) as exc_info:
                NodeBase(contract_path=contract_path, container=mock_container)

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Failed to import main tool class" in exc_info.value.message

    def test_should_fail_with_nonexistent_class(self, tmp_path, mock_container):
        """Test that nonexistent class in valid module raises error."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.NonexistentClass"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            with pytest.raises(ModelOnexError) as exc_info:
                NodeBase(contract_path=contract_path, container=mock_container)

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Class not found in module" in exc_info.value.message


# ===== ASYNC EXECUTION TESTS =====


class TestNodeBaseAsyncExecution:
    """Test NodeBase async execution methods."""

    @pytest.mark.asyncio
    async def test_should_execute_run_async_successfully(
        self, tmp_path, mock_container
    ):
        """Test run_async executes successfully."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            input_state = {"test": "input"}
            result = await node.run_async(input_state)

            assert result is not None
            assert result == {"result": "async_success"}
            assert node.main_tool.process_async_called

    @pytest.mark.asyncio
    async def test_should_execute_process_async_successfully(
        self, tmp_path, mock_container
    ):
        """Test process_async executes successfully."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            input_state = {"test": "input"}
            result = await node.process_async(input_state)

            assert result is not None
            assert result == {"result": "async_success"}

    @pytest.mark.asyncio
    async def test_should_handle_tool_with_sync_process_method(
        self, tmp_path, mock_container
    ):
        """Test handling tool with only sync process method."""
        contract_path = tmp_path / "test_contract.yaml"

        # Create a tool with only sync process method
        class SyncOnlyTool:
            def __init__(self, container=None):
                self.container = container

            def process(self, input_state):
                return {"result": "sync_only"}

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Replace tool with sync-only version
            node._main_tool = SyncOnlyTool(mock_container)

            input_state = {"test": "input"}
            result = await node.process_async(input_state)

            assert result == {"result": "sync_only"}

    @pytest.mark.asyncio
    async def test_should_handle_tool_with_run_method(self, tmp_path, mock_container):
        """Test handling tool with run method."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Replace tool with run-only version
            node._main_tool = MockToolWithRun(mock_container)

            input_state = {"test": "input"}
            result = await node.process_async(input_state)

            assert result == {"result": "run_success"}

    @pytest.mark.asyncio
    async def test_should_fail_when_tool_has_no_execution_method(
        self, tmp_path, mock_container
    ):
        """Test failure when tool has no process/run method."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Replace tool with no-methods version
            node._main_tool = MockToolNoMethods(mock_container)

            with pytest.raises(ModelOnexError) as exc_info:
                await node.process_async({"test": "input"})

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert (
                "does not implement process_async(), process(), or run() method"
                in exc_info.value.message
            )

    @pytest.mark.asyncio
    async def test_should_fail_when_main_tool_is_none(self, tmp_path, mock_container):
        """Test failure when main_tool is not initialized."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Set main_tool to None
            node._main_tool = None

            with pytest.raises(ModelOnexError) as exc_info:
                await node.process_async({"test": "input"})

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Main tool is not initialized" in exc_info.value.message


# ===== SYNC EXECUTION TESTS =====


class TestNodeBaseSyncExecution:
    """Test NodeBase sync execution methods."""

    def test_should_execute_run_successfully(self, tmp_path, mock_container):
        """Test run (sync) executes successfully."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            input_state = {"test": "input"}
            result = node.run(input_state)

            assert result is not None
            assert result == {"result": "async_success"}

    def test_should_execute_process_successfully(self, tmp_path, mock_container):
        """Test process (sync) executes successfully."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            input_state = {"test": "input"}
            result = node.process(input_state)

            assert result is not None
            assert result == {"result": "async_success"}


# ===== REDUCER PATTERN TESTS =====


class TestNodeBaseReducerPattern:
    """Test NodeBase reducer pattern implementation."""

    def test_should_return_initial_state(self, tmp_path, mock_container):
        """Test initial_state returns empty ModelState."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            state = node.initial_state()

            assert isinstance(state, ModelState)

    def test_should_dispatch_action_synchronously(self, tmp_path, mock_container):
        """Test dispatch returns unchanged state by default."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            state = ModelState()
            action = ModelAction(type="test_action")

            new_state = node.dispatch(state, action)

            assert new_state == state

    @pytest.mark.asyncio
    async def test_should_dispatch_action_asynchronously(
        self, tmp_path, mock_container
    ):
        """Test dispatch_async delegates to dispatch."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            state = ModelState()
            action = ModelAction(type="test_action")

            result = await node.dispatch_async(state, action)

            # dispatch_async returns ModelNodeWorkflowResult wrapping the state
            assert result.is_success
            assert isinstance(result.value, ModelState)


# ===== PROPERTY TESTS =====


class TestNodeBaseProperties:
    """Test NodeBase property accessors."""

    def test_should_access_container_property(self, tmp_path, mock_container):
        """Test container property access."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            container = node.container

            assert container is not None
            assert container == mock_container

    def test_should_fail_when_container_not_initialized(self, tmp_path):
        """Test container property raises error when not initialized."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path)

            # Force container to None
            node._container = None

            with pytest.raises(ModelOnexError) as exc_info:
                _ = node.container

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Container is not initialized" in exc_info.value.message

    def test_should_access_main_tool_property(self, tmp_path, mock_container):
        """Test main_tool property access."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            tool = node.main_tool

            assert tool is not None
            assert isinstance(tool, MockTool)

    def test_should_access_current_state_property(self, tmp_path, mock_container):
        """Test current_state property access."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            state = node.current_state

            assert isinstance(state, ModelState)

    def test_should_fail_when_current_state_not_initialized(
        self, tmp_path, mock_container
    ):
        """Test current_state property raises error when not initialized."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Force reducer_state to None
            node._reducer_state = None

            with pytest.raises(ModelOnexError) as exc_info:
                _ = node.current_state

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "Reducer state is not initialized" in exc_info.value.message

    def test_should_access_workflow_instance_property(self, tmp_path, mock_container):
        """Test workflow_instance property access."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Default implementation returns None
            workflow = node.workflow_instance

            assert workflow is None


# ===== WORKFLOW TESTS =====


class TestNodeBaseWorkflow:
    """Test NodeBase workflow creation."""

    def test_should_return_none_for_default_workflow(self, tmp_path, mock_container):
        """Test create_workflow returns None by default."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            workflow = node.workflow_instance

            assert workflow is None


# ===== EDGE CASES AND ERROR HANDLING =====


class TestNodeBaseEdgeCases:
    """Test NodeBase edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_should_handle_exception_during_execution(
        self, tmp_path, mock_container
    ):
        """Test exception handling during execution."""
        contract_path = tmp_path / "test_contract.yaml"

        # Create a tool that raises an exception
        class FailingTool:
            def __init__(self, container=None):
                self.container = container

            async def process_async(self, input_state):
                raise ValueError("Tool execution failed")

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Replace tool with failing version
            node._main_tool = FailingTool(mock_container)

            with pytest.raises(ModelOnexError) as exc_info:
                await node.run_async({"test": "input"})

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_should_preserve_onex_error_during_execution(
        self, tmp_path, mock_container
    ):
        """Test that OnexError is preserved during execution."""
        contract_path = tmp_path / "test_contract.yaml"

        # Create a tool that raises OnexError
        class OnexErrorTool:
            def __init__(self, container=None):
                self.container = container

            async def process_async(self, input_state):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Validation failed in tool",
                )

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Replace tool with OnexError-raising version
            node._main_tool = OnexErrorTool(mock_container)

            with pytest.raises(ModelOnexError) as exc_info:
                await node.run_async({"test": "input"})

            # Should preserve the original OnexError
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Validation failed in tool" in exc_info.value.message

    def test_should_handle_dependencies_in_contract(self, tmp_path, mock_container):
        """Test handling of contract dependencies."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)

            # Create mock dependencies
            dep1 = Mock()
            dep1.name = "dependency1"
            dep1.module = "module1"
            dep1.type = "service"
            dep1.required = True

            mock_contract.dependencies = [dep1, "string_dependency"]

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            # Should not raise - dependencies are logged but not enforced yet
            node = NodeBase(contract_path=contract_path, container=mock_container)

            assert node is not None

    @pytest.mark.asyncio
    async def test_should_handle_dispatch_async_error(self, tmp_path, mock_container):
        """Test exception handling in dispatch_async."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Override dispatch to raise exception
            def failing_dispatch(state, action):
                raise RuntimeError("Dispatch failed")

            node.dispatch = failing_dispatch

            state = ModelState()
            action = ModelAction(type="test_action")

            with pytest.raises(ModelOnexError) as exc_info:
                await node.dispatch_async(state, action)

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert "State dispatch failed" in exc_info.value.message

    def test_should_handle_none_business_logic_pattern(self, tmp_path, mock_container):
        """Test handling of None business_logic_pattern."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = None  # Test None case
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Should set pattern_value to "unknown"
            assert node.state.node_classification == "unknown"

    def test_should_handle_enum_business_logic_pattern(self, tmp_path, mock_container):
        """Test handling of enum business_logic_pattern."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)
            mock_contract.dependencies = []

            tool_spec = Mock()
            # Create mock enum with value attribute
            enum_pattern = Mock()
            enum_pattern.value = "enum_pattern_value"
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = enum_pattern
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            node = NodeBase(contract_path=contract_path, container=mock_container)

            # Should extract value from enum
            assert node.state.node_classification == "enum_pattern_value"

    def test_should_handle_enum_dependency_type(self, tmp_path, mock_container):
        """Test handling of enum type in dependencies."""
        contract_path = tmp_path / "test_contract.yaml"

        with patch(
            "omnibase_core.utils.util_contract_loader.ProtocolContractLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_contract = Mock()
            mock_contract.node_name = "test_node"
            mock_contract.contract_version = ModelSemVer(major=1, minor=0, patch=0)

            # Create mock dependency with enum type
            dep = Mock()
            dep.name = "test_dep"
            dep.module = "test_module"
            enum_type = Mock()
            enum_type.value = "enum_service_type"
            dep.type = enum_type
            dep.required = True

            mock_contract.dependencies = [dep]

            tool_spec = Mock()
            tool_spec.main_tool_class = (
                "tests.unit.infrastructure.test_node_base.MockTool"
            )
            tool_spec.business_logic_pattern = "test_pattern"
            mock_contract.tool_specification = tool_spec

            mock_loader.load_contract.return_value = mock_contract
            mock_loader_class.return_value = mock_loader

            # Should handle enum type extraction
            node = NodeBase(contract_path=contract_path, container=mock_container)

            assert node is not None
