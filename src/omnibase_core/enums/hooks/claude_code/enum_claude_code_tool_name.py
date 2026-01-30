"""Enumeration of Claude Code tool names.

Defines the canonical tool names used by Claude Code for tool execution tracking.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumClaudeCodeToolName(StrValueHelper, str, Enum):
    """Claude Code built-in tool names.

    Used for classifying tool executions in pattern learning and analytics.
    UNKNOWN is used for forward compatibility when new tools are added.

    Tool Categories:
        - File operations: READ, WRITE, EDIT
        - Search operations: GLOB, GREP
        - Execution: BASH, TASK
        - Web operations: WEB_FETCH, WEB_SEARCH
        - Notebook: NOTEBOOK_EDIT
        - Task management: TASK_CREATE, TASK_GET, TASK_UPDATE, TASK_LIST
        - Skills: SKILL
        - MCP: MCP (prefix for Model Context Protocol tools)
    """

    # File operations
    READ = "Read"
    """Read file contents from the filesystem."""

    WRITE = "Write"
    """Write content to a file on the filesystem."""

    EDIT = "Edit"
    """Edit existing file with string replacement."""

    # Search operations
    GLOB = "Glob"
    """Find files by glob pattern."""

    GREP = "Grep"
    """Search file contents with regex patterns."""

    # Execution
    BASH = "Bash"
    """Execute shell commands."""

    TASK = "Task"
    """Delegate work to a subagent."""

    # Web operations
    WEB_FETCH = "WebFetch"
    """Fetch and process content from a URL."""

    WEB_SEARCH = "WebSearch"
    """Search the web for information."""

    # Notebook
    NOTEBOOK_EDIT = "NotebookEdit"
    """Edit Jupyter notebook cells."""

    # Task management
    TASK_CREATE = "TaskCreate"
    """Create a new task in the task list."""

    TASK_GET = "TaskGet"
    """Get task details by ID."""

    TASK_UPDATE = "TaskUpdate"
    """Update an existing task."""

    TASK_LIST = "TaskList"
    """List all tasks in the task list."""

    # Skills
    SKILL = "Skill"
    """Invoke a skill within the conversation."""

    # MCP (Model Context Protocol)
    MCP = "mcp"
    """MCP tool invocation (prefix pattern: mcp__server__tool)."""

    # Forward compatibility
    UNKNOWN = "Unknown"
    """Unknown tool name for forward compatibility."""

    @classmethod
    def from_string(cls, value: str) -> EnumClaudeCodeToolName:
        """Convert string to enum, returning UNKNOWN for unrecognized values.

        Handles MCP tool names by returning MCP for any tool starting with 'mcp__'.

        Args:
            value: The tool name string to convert.

        Returns:
            The matching enum member, MCP for mcp__* tools, or UNKNOWN if not found.
        """
        # Handle MCP tool prefix pattern
        if value.startswith("mcp__"):
            return cls.MCP

        for member in cls:
            if member.value == value:
                return member
        return cls.UNKNOWN

    @classmethod
    def is_file_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a file operation."""
        return tool in {cls.READ, cls.WRITE, cls.EDIT}

    @classmethod
    def is_search_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a search operation."""
        return tool in {cls.GLOB, cls.GREP}

    @classmethod
    def is_execution_tool(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is an execution tool."""
        return tool in {cls.BASH, cls.TASK}

    @classmethod
    def is_web_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a web operation."""
        return tool in {cls.WEB_FETCH, cls.WEB_SEARCH}

    @classmethod
    def is_task_management(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a task management tool."""
        return tool in {cls.TASK_CREATE, cls.TASK_GET, cls.TASK_UPDATE, cls.TASK_LIST}


__all__ = ["EnumClaudeCodeToolName"]
