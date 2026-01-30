"""Tests for EnumClaudeCodeToolName (OMN-1701).

Tests comprehensive enum functionality including:
- All members have correct values
- from_string() returns correct enum for known tools
- from_string() returns UNKNOWN for unrecognized tools
- MCP tool pattern handling (mcp__* prefix)
- Helper methods (is_file_operation, is_search_operation, etc.)
- StrValueHelper provides correct __str__ behavior
- Import verification
"""

from __future__ import annotations

import json
from enum import Enum

import pytest

from omnibase_core.enums.hooks.claude_code import EnumClaudeCodeToolName
from omnibase_core.utils.util_str_enum_base import StrValueHelper

pytestmark = pytest.mark.unit


# ============================================================================
# Test: Enum Values
# ============================================================================


class TestEnumClaudeCodeToolNameValues:
    """Tests for enum value definitions."""

    def test_file_operation_values(self) -> None:
        """Test file operation tool values."""
        assert EnumClaudeCodeToolName.READ.value == "Read"
        assert EnumClaudeCodeToolName.WRITE.value == "Write"
        assert EnumClaudeCodeToolName.EDIT.value == "Edit"

    def test_ls_value(self) -> None:
        """Test LS tool value."""
        assert EnumClaudeCodeToolName.LS.value == "LS"

    def test_search_operation_values(self) -> None:
        """Test search operation tool values."""
        assert EnumClaudeCodeToolName.GLOB.value == "Glob"
        assert EnumClaudeCodeToolName.GREP.value == "Grep"

    def test_execution_tool_values(self) -> None:
        """Test execution tool values."""
        assert EnumClaudeCodeToolName.BASH.value == "Bash"
        assert EnumClaudeCodeToolName.TASK.value == "Task"

    def test_task_stop_value(self) -> None:
        """Test TaskStop tool value."""
        assert EnumClaudeCodeToolName.TASK_STOP.value == "TaskStop"

    def test_task_output_value(self) -> None:
        """Test TaskOutput tool value."""
        assert EnumClaudeCodeToolName.TASK_OUTPUT.value == "TaskOutput"

    def test_bash_output_value(self) -> None:
        """Test BashOutput tool value."""
        assert EnumClaudeCodeToolName.BASH_OUTPUT.value == "BashOutput"

    def test_kill_shell_value(self) -> None:
        """Test KillShell tool value."""
        assert EnumClaudeCodeToolName.KILL_SHELL.value == "KillShell"

    def test_web_operation_values(self) -> None:
        """Test web operation tool values."""
        assert EnumClaudeCodeToolName.WEB_FETCH.value == "WebFetch"
        assert EnumClaudeCodeToolName.WEB_SEARCH.value == "WebSearch"

    def test_notebook_tool_values(self) -> None:
        """Test notebook tool values."""
        assert EnumClaudeCodeToolName.NOTEBOOK_EDIT.value == "NotebookEdit"

    def test_notebook_read_value(self) -> None:
        """Test NotebookRead tool value."""
        assert EnumClaudeCodeToolName.NOTEBOOK_READ.value == "NotebookRead"

    def test_task_management_values(self) -> None:
        """Test task management tool values."""
        assert EnumClaudeCodeToolName.TASK_CREATE.value == "TaskCreate"
        assert EnumClaudeCodeToolName.TASK_GET.value == "TaskGet"
        assert EnumClaudeCodeToolName.TASK_UPDATE.value == "TaskUpdate"
        assert EnumClaudeCodeToolName.TASK_LIST.value == "TaskList"

    def test_user_interaction_values(self) -> None:
        """Test user interaction tool values."""
        assert EnumClaudeCodeToolName.ASK_USER_QUESTION.value == "AskUserQuestion"

    def test_plan_mode_values(self) -> None:
        """Test plan mode tool values."""
        assert EnumClaudeCodeToolName.ENTER_PLAN_MODE.value == "EnterPlanMode"
        assert EnumClaudeCodeToolName.EXIT_PLAN_MODE.value == "ExitPlanMode"

    def test_skill_tool_values(self) -> None:
        """Test skill tool values."""
        assert EnumClaudeCodeToolName.SKILL.value == "Skill"

    def test_mcp_tool_values(self) -> None:
        """Test MCP tool sentinel value (PascalCase for consistency)."""
        assert EnumClaudeCodeToolName.MCP.value == "Mcp"

    def test_unknown_value(self) -> None:
        """Test UNKNOWN fallback value."""
        assert EnumClaudeCodeToolName.UNKNOWN.value == "Unknown"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 26 values."""
        values = list(EnumClaudeCodeToolName)
        assert len(values) == 26

    def test_all_expected_values_present(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "Read",
            "Write",
            "Edit",
            "LS",
            "Glob",
            "Grep",
            "Bash",
            "BashOutput",
            "Task",
            "TaskStop",
            "TaskOutput",
            "KillShell",
            "WebFetch",
            "WebSearch",
            "NotebookEdit",
            "NotebookRead",
            "TaskCreate",
            "TaskGet",
            "TaskUpdate",
            "TaskList",
            "AskUserQuestion",
            "EnterPlanMode",
            "ExitPlanMode",
            "Skill",
            "Mcp",
            "Unknown",
        }
        actual_values = {member.value for member in EnumClaudeCodeToolName}
        assert actual_values == expected_values


# ============================================================================
# Test: Enum Inheritance and String Behavior
# ============================================================================


class TestEnumClaudeCodeToolNameInheritance:
    """Tests for enum inheritance and string behavior."""

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from StrValueHelper, str, and Enum."""
        assert issubclass(EnumClaudeCodeToolName, StrValueHelper)
        assert issubclass(EnumClaudeCodeToolName, str)
        assert issubclass(EnumClaudeCodeToolName, Enum)

    def test_str_value_helper_behavior(self) -> None:
        """Test that StrValueHelper provides correct __str__ behavior."""
        assert str(EnumClaudeCodeToolName.READ) == "Read"
        assert str(EnumClaudeCodeToolName.BASH) == "Bash"
        assert str(EnumClaudeCodeToolName.WEB_FETCH) == "WebFetch"
        assert str(EnumClaudeCodeToolName.UNKNOWN) == "Unknown"

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings due to str inheritance."""
        tool = EnumClaudeCodeToolName.READ
        assert isinstance(tool, str)
        assert tool == "Read"
        assert len(tool) == 4
        assert tool.startswith("R")

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated."""
        values = list(EnumClaudeCodeToolName)
        assert EnumClaudeCodeToolName.READ in values
        assert EnumClaudeCodeToolName.BASH in values
        assert EnumClaudeCodeToolName.UNKNOWN in values

    def test_enum_membership(self) -> None:
        """Test enum membership operations."""
        assert "Read" in EnumClaudeCodeToolName
        assert "Bash" in EnumClaudeCodeToolName
        assert "InvalidTool" not in EnumClaudeCodeToolName

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        tool1 = EnumClaudeCodeToolName.READ
        tool2 = EnumClaudeCodeToolName.WRITE
        tool3 = EnumClaudeCodeToolName.READ

        assert tool1 != tool2
        assert tool1 == tool3
        assert tool1 == "Read"
        assert tool2 == "Write"


# ============================================================================
# Test: Serialization
# ============================================================================


class TestEnumClaudeCodeToolNameSerialization:
    """Tests for enum serialization."""

    def test_enum_value_serialization(self) -> None:
        """Test that enum values can be serialized."""
        tool = EnumClaudeCodeToolName.BASH
        serialized = tool.value
        assert serialized == "Bash"

    def test_json_serialization(self) -> None:
        """Test that enum values can be serialized to JSON."""
        tool = EnumClaudeCodeToolName.WEB_FETCH
        json_str = json.dumps(tool)
        assert json_str == '"WebFetch"'

    def test_enum_deserialization(self) -> None:
        """Test that enum can be created from string values."""
        tool = EnumClaudeCodeToolName("Read")
        assert tool == EnumClaudeCodeToolName.READ

        tool = EnumClaudeCodeToolName("TaskCreate")
        assert tool == EnumClaudeCodeToolName.TASK_CREATE

    def test_enum_invalid_direct_creation(self) -> None:
        """Test that invalid values raise ValueError for direct creation."""
        with pytest.raises(ValueError):
            EnumClaudeCodeToolName("InvalidTool")

        with pytest.raises(ValueError):
            EnumClaudeCodeToolName("read")  # Wrong case


# ============================================================================
# Test: from_string() Classmethod
# ============================================================================


class TestEnumClaudeCodeToolNameFromString:
    """Tests for from_string() classmethod."""

    def test_from_string_known_tools(self) -> None:
        """Test from_string returns correct enum for known tools."""
        assert EnumClaudeCodeToolName.from_string("Read") == EnumClaudeCodeToolName.READ
        assert (
            EnumClaudeCodeToolName.from_string("Write") == EnumClaudeCodeToolName.WRITE
        )
        assert EnumClaudeCodeToolName.from_string("Edit") == EnumClaudeCodeToolName.EDIT
        assert EnumClaudeCodeToolName.from_string("LS") == EnumClaudeCodeToolName.LS
        assert EnumClaudeCodeToolName.from_string("Glob") == EnumClaudeCodeToolName.GLOB
        assert EnumClaudeCodeToolName.from_string("Grep") == EnumClaudeCodeToolName.GREP
        assert EnumClaudeCodeToolName.from_string("Bash") == EnumClaudeCodeToolName.BASH
        assert EnumClaudeCodeToolName.from_string("Task") == EnumClaudeCodeToolName.TASK
        assert (
            EnumClaudeCodeToolName.from_string("WebFetch")
            == EnumClaudeCodeToolName.WEB_FETCH
        )
        assert (
            EnumClaudeCodeToolName.from_string("WebSearch")
            == EnumClaudeCodeToolName.WEB_SEARCH
        )
        assert (
            EnumClaudeCodeToolName.from_string("NotebookEdit")
            == EnumClaudeCodeToolName.NOTEBOOK_EDIT
        )
        assert (
            EnumClaudeCodeToolName.from_string("NotebookRead")
            == EnumClaudeCodeToolName.NOTEBOOK_READ
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskCreate")
            == EnumClaudeCodeToolName.TASK_CREATE
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskGet")
            == EnumClaudeCodeToolName.TASK_GET
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskUpdate")
            == EnumClaudeCodeToolName.TASK_UPDATE
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskList")
            == EnumClaudeCodeToolName.TASK_LIST
        )
        assert (
            EnumClaudeCodeToolName.from_string("AskUserQuestion")
            == EnumClaudeCodeToolName.ASK_USER_QUESTION
        )
        assert (
            EnumClaudeCodeToolName.from_string("EnterPlanMode")
            == EnumClaudeCodeToolName.ENTER_PLAN_MODE
        )
        assert (
            EnumClaudeCodeToolName.from_string("ExitPlanMode")
            == EnumClaudeCodeToolName.EXIT_PLAN_MODE
        )
        assert (
            EnumClaudeCodeToolName.from_string("Skill") == EnumClaudeCodeToolName.SKILL
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskStop")
            == EnumClaudeCodeToolName.TASK_STOP
        )
        assert (
            EnumClaudeCodeToolName.from_string("TaskOutput")
            == EnumClaudeCodeToolName.TASK_OUTPUT
        )
        assert (
            EnumClaudeCodeToolName.from_string("BashOutput")
            == EnumClaudeCodeToolName.BASH_OUTPUT
        )
        assert (
            EnumClaudeCodeToolName.from_string("KillShell")
            == EnumClaudeCodeToolName.KILL_SHELL
        )

    def test_from_string_unknown_tools(self) -> None:
        """Test from_string returns UNKNOWN for unrecognized tools."""
        assert (
            EnumClaudeCodeToolName.from_string("UnknownTool")
            == EnumClaudeCodeToolName.UNKNOWN
        )
        assert (
            EnumClaudeCodeToolName.from_string("SomeFutureTool")
            == EnumClaudeCodeToolName.UNKNOWN
        )
        assert EnumClaudeCodeToolName.from_string("") == EnumClaudeCodeToolName.UNKNOWN
        assert (
            EnumClaudeCodeToolName.from_string("read") == EnumClaudeCodeToolName.UNKNOWN
        )  # Wrong case

    def test_from_string_mcp_tools(self) -> None:
        """Test from_string handles MCP tool prefix pattern."""
        # MCP tools start with 'mcp__'
        assert (
            EnumClaudeCodeToolName.from_string("mcp__linear-server__list_issues")
            == EnumClaudeCodeToolName.MCP
        )
        assert (
            EnumClaudeCodeToolName.from_string("mcp__github__create_pr")
            == EnumClaudeCodeToolName.MCP
        )
        assert (
            EnumClaudeCodeToolName.from_string("mcp__some_server__any_tool")
            == EnumClaudeCodeToolName.MCP
        )
        assert (
            EnumClaudeCodeToolName.from_string("mcp__") == EnumClaudeCodeToolName.MCP
        )  # Just prefix

    def test_from_string_mcp_like_but_not_mcp(self) -> None:
        """Test from_string does not match non-MCP patterns."""
        # "Mcp" is the actual enum value (PascalCase sentinel)
        assert EnumClaudeCodeToolName.from_string("Mcp") == EnumClaudeCodeToolName.MCP
        # "mcp" (lowercase) is NOT the enum value - returns UNKNOWN
        assert (
            EnumClaudeCodeToolName.from_string("mcp") == EnumClaudeCodeToolName.UNKNOWN
        )
        # Single underscore is not valid MCP prefix pattern
        assert (
            EnumClaudeCodeToolName.from_string("mcp_single_underscore")
            == EnumClaudeCodeToolName.UNKNOWN
        )
        # Capitalized prefix is not valid (prefix check is lowercase mcp__)
        assert (
            EnumClaudeCodeToolName.from_string("Mcp__capitalized")
            == EnumClaudeCodeToolName.UNKNOWN
        )

    def test_from_string_does_not_raise(self) -> None:
        """Test from_string never raises - returns UNKNOWN instead."""
        # These would raise if using direct enum construction
        result = EnumClaudeCodeToolName.from_string("completely invalid!@#$%")
        assert result == EnumClaudeCodeToolName.UNKNOWN


# ============================================================================
# Test: Helper Methods - is_file_operation
# ============================================================================


class TestEnumClaudeCodeToolNameIsFileOperation:
    """Tests for is_file_operation helper method."""

    def test_file_operations_return_true(self) -> None:
        """Test that file operation tools return True."""
        file_ops = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
        ]

        for tool in file_ops:
            assert EnumClaudeCodeToolName.is_file_operation(tool) is True, (
                f"Expected {tool} to be a file operation"
            )

    def test_non_file_operations_return_false(self) -> None:
        """Test that non-file-operation tools return False."""
        non_file_ops = [
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_file_ops:
            assert EnumClaudeCodeToolName.is_file_operation(tool) is False, (
                f"Expected {tool} to NOT be a file operation"
            )

    def test_file_operation_count(self) -> None:
        """Test that exactly 4 tools are file operations."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_file_operation(tool)
        )
        assert count == 4


# ============================================================================
# Test: Helper Methods - is_search_operation
# ============================================================================


class TestEnumClaudeCodeToolNameIsSearchOperation:
    """Tests for is_search_operation helper method."""

    def test_search_operations_return_true(self) -> None:
        """Test that search operation tools return True."""
        search_ops = [
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
        ]

        for tool in search_ops:
            assert EnumClaudeCodeToolName.is_search_operation(tool) is True, (
                f"Expected {tool} to be a search operation"
            )

    def test_non_search_operations_return_false(self) -> None:
        """Test that non-search-operation tools return False."""
        non_search_ops = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_search_ops:
            assert EnumClaudeCodeToolName.is_search_operation(tool) is False, (
                f"Expected {tool} to NOT be a search operation"
            )

    def test_search_operation_count(self) -> None:
        """Test that exactly 2 tools are search operations."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_search_operation(tool)
        )
        assert count == 2


# ============================================================================
# Test: Helper Methods - is_execution_tool
# ============================================================================


class TestEnumClaudeCodeToolNameIsExecutionTool:
    """Tests for is_execution_tool helper method."""

    def test_execution_tools_return_true(self) -> None:
        """Test that execution tools return True."""
        exec_tools = [
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
        ]

        for tool in exec_tools:
            assert EnumClaudeCodeToolName.is_execution_tool(tool) is True, (
                f"Expected {tool} to be an execution tool"
            )

    def test_non_execution_tools_return_false(self) -> None:
        """Test that non-execution tools return False."""
        non_exec_tools = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_exec_tools:
            assert EnumClaudeCodeToolName.is_execution_tool(tool) is False, (
                f"Expected {tool} to NOT be an execution tool"
            )

    def test_execution_tool_count(self) -> None:
        """Test that exactly 4 tools are execution tools."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_execution_tool(tool)
        )
        assert count == 4


# ============================================================================
# Test: Helper Methods - is_web_operation
# ============================================================================


class TestEnumClaudeCodeToolNameIsWebOperation:
    """Tests for is_web_operation helper method."""

    def test_web_operations_return_true(self) -> None:
        """Test that web operation tools return True."""
        web_ops = [
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
        ]

        for tool in web_ops:
            assert EnumClaudeCodeToolName.is_web_operation(tool) is True, (
                f"Expected {tool} to be a web operation"
            )

    def test_non_web_operations_return_false(self) -> None:
        """Test that non-web-operation tools return False."""
        non_web_ops = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_web_ops:
            assert EnumClaudeCodeToolName.is_web_operation(tool) is False, (
                f"Expected {tool} to NOT be a web operation"
            )

    def test_web_operation_count(self) -> None:
        """Test that exactly 2 tools are web operations."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_web_operation(tool)
        )
        assert count == 2


# ============================================================================
# Test: Helper Methods - is_task_management
# ============================================================================


class TestEnumClaudeCodeToolNameIsTaskManagement:
    """Tests for is_task_management helper method."""

    def test_task_management_tools_return_true(self) -> None:
        """Test that task management tools return True."""
        task_mgmt_tools = [
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
        ]

        for tool in task_mgmt_tools:
            assert EnumClaudeCodeToolName.is_task_management(tool) is True, (
                f"Expected {tool} to be a task management tool"
            )

    def test_non_task_management_tools_return_false(self) -> None:
        """Test that non-task-management tools return False."""
        non_task_mgmt = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,  # Note: TASK is for subagent delegation, not task list
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_task_mgmt:
            assert EnumClaudeCodeToolName.is_task_management(tool) is False, (
                f"Expected {tool} to NOT be a task management tool"
            )

    def test_task_management_count(self) -> None:
        """Test that exactly 6 tools are task management tools."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_task_management(tool)
        )
        assert count == 6


# ============================================================================
# Test: Helper Methods - is_notebook_operation
# ============================================================================


class TestEnumClaudeCodeToolNameIsNotebookOperation:
    """Tests for is_notebook_operation helper method."""

    def test_notebook_operations_return_true(self) -> None:
        """Test that notebook operation tools return True."""
        notebook_ops = [
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
        ]

        for tool in notebook_ops:
            assert EnumClaudeCodeToolName.is_notebook_operation(tool) is True, (
                f"Expected {tool} to be a notebook operation"
            )

    def test_non_notebook_operations_return_false(self) -> None:
        """Test that non-notebook-operation tools return False."""
        non_notebook_ops = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_notebook_ops:
            assert EnumClaudeCodeToolName.is_notebook_operation(tool) is False, (
                f"Expected {tool} to NOT be a notebook operation"
            )

    def test_notebook_operation_count(self) -> None:
        """Test that exactly 2 tools are notebook operations."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_notebook_operation(tool)
        )
        assert count == 2


# ============================================================================
# Test: Helper Methods - is_user_interaction
# ============================================================================


class TestEnumClaudeCodeToolNameIsUserInteraction:
    """Tests for is_user_interaction helper method."""

    def test_user_interaction_returns_true(self) -> None:
        """Test that ASK_USER_QUESTION returns True."""
        assert (
            EnumClaudeCodeToolName.is_user_interaction(
                EnumClaudeCodeToolName.ASK_USER_QUESTION
            )
            is True
        )

    def test_non_user_interaction_returns_false(self) -> None:
        """Test that other tools return False."""
        non_user_interaction = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_user_interaction:
            assert EnumClaudeCodeToolName.is_user_interaction(tool) is False, (
                f"Expected {tool} to NOT be a user interaction tool"
            )

    def test_user_interaction_count(self) -> None:
        """Test that exactly 1 tool is user interaction."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_user_interaction(tool)
        )
        assert count == 1


# ============================================================================
# Test: Helper Methods - is_plan_mode
# ============================================================================


class TestEnumClaudeCodeToolNameIsPlanMode:
    """Tests for is_plan_mode helper method."""

    def test_plan_mode_tools_return_true(self) -> None:
        """Test that plan mode tools return True."""
        plan_mode_tools = [
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
        ]

        for tool in plan_mode_tools:
            assert EnumClaudeCodeToolName.is_plan_mode(tool) is True, (
                f"Expected {tool} to be a plan mode tool"
            )

    def test_non_plan_mode_returns_false(self) -> None:
        """Test that other tools return False."""
        non_plan_mode = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in non_plan_mode:
            assert EnumClaudeCodeToolName.is_plan_mode(tool) is False, (
                f"Expected {tool} to NOT be a plan mode tool"
            )

    def test_plan_mode_count(self) -> None:
        """Test that exactly 2 tools are plan mode tools."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_plan_mode(tool)
        )
        assert count == 2


# ============================================================================
# Test: Helper Methods - is_skill
# ============================================================================


class TestEnumClaudeCodeToolNameIsSkill:
    """Tests for is_skill helper method."""

    def test_skill_returns_true(self) -> None:
        """Test that SKILL returns True."""
        assert EnumClaudeCodeToolName.is_skill(EnumClaudeCodeToolName.SKILL) is True

    def test_non_skill_returns_false(self) -> None:
        """Test that other tools return False."""
        # Test a few representative tools
        assert EnumClaudeCodeToolName.is_skill(EnumClaudeCodeToolName.READ) is False
        assert EnumClaudeCodeToolName.is_skill(EnumClaudeCodeToolName.BASH) is False
        assert EnumClaudeCodeToolName.is_skill(EnumClaudeCodeToolName.MCP) is False

    def test_skill_count(self) -> None:
        """Test that exactly 1 tool is skill."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_skill(tool)
        )
        assert count == 1


# ============================================================================
# Test: Helper Methods - is_mcp_tool
# ============================================================================


class TestEnumClaudeCodeToolNameIsMcpTool:
    """Tests for is_mcp_tool helper method."""

    def test_mcp_returns_true(self) -> None:
        """Test that MCP returns True."""
        assert EnumClaudeCodeToolName.is_mcp_tool(EnumClaudeCodeToolName.MCP) is True

    def test_non_mcp_returns_false(self) -> None:
        """Test that other tools return False."""
        assert EnumClaudeCodeToolName.is_mcp_tool(EnumClaudeCodeToolName.READ) is False
        assert EnumClaudeCodeToolName.is_mcp_tool(EnumClaudeCodeToolName.SKILL) is False

    def test_mcp_tool_count(self) -> None:
        """Test that exactly 1 tool is MCP."""
        count = sum(
            1
            for tool in EnumClaudeCodeToolName
            if EnumClaudeCodeToolName.is_mcp_tool(tool)
        )
        assert count == 1


# ============================================================================
# Test: Category Exclusivity
# ============================================================================


class TestEnumClaudeCodeToolNameCategoryExclusivity:
    """Tests for category exclusivity - tools in one category only."""

    def test_categories_are_mutually_exclusive(self) -> None:
        """Test that non-UNKNOWN tools are in exactly one category."""
        # Tools that should be in exactly one main category
        categorized_tools = [
            EnumClaudeCodeToolName.READ,
            EnumClaudeCodeToolName.WRITE,
            EnumClaudeCodeToolName.EDIT,
            EnumClaudeCodeToolName.LS,
            EnumClaudeCodeToolName.GLOB,
            EnumClaudeCodeToolName.GREP,
            EnumClaudeCodeToolName.BASH,
            EnumClaudeCodeToolName.BASH_OUTPUT,
            EnumClaudeCodeToolName.TASK,
            EnumClaudeCodeToolName.KILL_SHELL,
            EnumClaudeCodeToolName.WEB_FETCH,
            EnumClaudeCodeToolName.WEB_SEARCH,
            EnumClaudeCodeToolName.NOTEBOOK_EDIT,
            EnumClaudeCodeToolName.NOTEBOOK_READ,
            EnumClaudeCodeToolName.TASK_CREATE,
            EnumClaudeCodeToolName.TASK_GET,
            EnumClaudeCodeToolName.TASK_UPDATE,
            EnumClaudeCodeToolName.TASK_LIST,
            EnumClaudeCodeToolName.TASK_STOP,
            EnumClaudeCodeToolName.TASK_OUTPUT,
            EnumClaudeCodeToolName.ASK_USER_QUESTION,
            EnumClaudeCodeToolName.ENTER_PLAN_MODE,
            EnumClaudeCodeToolName.EXIT_PLAN_MODE,
            EnumClaudeCodeToolName.SKILL,
            EnumClaudeCodeToolName.MCP,
        ]

        for tool in categorized_tools:
            categories = []
            if EnumClaudeCodeToolName.is_file_operation(tool):
                categories.append("file")
            if EnumClaudeCodeToolName.is_search_operation(tool):
                categories.append("search")
            if EnumClaudeCodeToolName.is_execution_tool(tool):
                categories.append("execution")
            if EnumClaudeCodeToolName.is_web_operation(tool):
                categories.append("web")
            if EnumClaudeCodeToolName.is_task_management(tool):
                categories.append("task_management")
            if EnumClaudeCodeToolName.is_notebook_operation(tool):
                categories.append("notebook")
            if EnumClaudeCodeToolName.is_user_interaction(tool):
                categories.append("user_interaction")
            if EnumClaudeCodeToolName.is_plan_mode(tool):
                categories.append("plan_mode")
            if EnumClaudeCodeToolName.is_skill(tool):
                categories.append("skill")
            if EnumClaudeCodeToolName.is_mcp_tool(tool):
                categories.append("mcp")

            assert len(categories) == 1, (
                f"Tool {tool} should be in exactly one category, found: {categories}"
            )

    def test_uncategorized_tools(self) -> None:
        """Test that UNKNOWN is not in any category."""
        uncategorized = [
            EnumClaudeCodeToolName.UNKNOWN,
        ]

        for tool in uncategorized:
            is_categorized = (
                EnumClaudeCodeToolName.is_file_operation(tool)
                or EnumClaudeCodeToolName.is_search_operation(tool)
                or EnumClaudeCodeToolName.is_execution_tool(tool)
                or EnumClaudeCodeToolName.is_web_operation(tool)
                or EnumClaudeCodeToolName.is_task_management(tool)
                or EnumClaudeCodeToolName.is_notebook_operation(tool)
                or EnumClaudeCodeToolName.is_user_interaction(tool)
                or EnumClaudeCodeToolName.is_plan_mode(tool)
                or EnumClaudeCodeToolName.is_skill(tool)
                or EnumClaudeCodeToolName.is_mcp_tool(tool)
            )
            assert is_categorized is False, f"Tool {tool} should not be in any category"


# ============================================================================
# Test: Docstring
# ============================================================================


class TestEnumClaudeCodeToolNameDocstring:
    """Tests for enum docstring."""

    def test_enum_has_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumClaudeCodeToolName.__doc__ is not None
        assert "Claude Code" in EnumClaudeCodeToolName.__doc__

    def test_docstring_mentions_categories(self) -> None:
        """Test that docstring documents tool categories."""
        docstring = EnumClaudeCodeToolName.__doc__ or ""
        assert "File operations" in docstring
        assert "Search operations" in docstring
        assert "Execution" in docstring
        assert "Web operations" in docstring
        assert "Task management" in docstring
        assert "Notebook" in docstring
        assert "User interaction" in docstring
        assert "Plan mode" in docstring


# ============================================================================
# Test: Import Verification
# ============================================================================


class TestEnumClaudeCodeToolNameImport:
    """Tests for enum import from package."""

    def test_import_from_hooks_claude_code(self) -> None:
        """Test import from enums.hooks.claude_code package."""
        from omnibase_core.enums.hooks.claude_code import (
            EnumClaudeCodeToolName as Imported,
        )

        assert Imported is EnumClaudeCodeToolName

    def test_enum_in_all(self) -> None:
        """Test that enum is in __all__."""
        from omnibase_core.enums.hooks import claude_code

        assert "EnumClaudeCodeToolName" in claude_code.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
