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
        - File operations: READ, WRITE, EDIT, LS
        - Search operations: GLOB, GREP
        - Execution: BASH, BASH_OUTPUT, TASK, KILL_SHELL
        - Web operations: WEB_FETCH, WEB_SEARCH
        - Notebook: NOTEBOOK_EDIT, NOTEBOOK_READ
        - Task management: TASK_CREATE, TASK_GET, TASK_UPDATE, TASK_LIST,
            TASK_STOP, TASK_OUTPUT
        - User interaction: ASK_USER_QUESTION
        - Plan mode: ENTER_PLAN_MODE, EXIT_PLAN_MODE
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

    LS = "LS"
    """List directory contents."""

    # Search operations
    GLOB = "Glob"
    """Find files by glob pattern."""

    GREP = "Grep"
    """Search file contents with regex patterns."""

    # Execution
    BASH = "Bash"
    """Execute shell commands."""

    BASH_OUTPUT = "BashOutput"
    """Get output from a running bash command."""

    TASK = "Task"
    """Delegate work to a subagent."""

    KILL_SHELL = "KillShell"
    """Kill a shell process."""

    # Web operations
    WEB_FETCH = "WebFetch"
    """Fetch and process content from a URL."""

    WEB_SEARCH = "WebSearch"
    """Search the web for information."""

    # Notebook
    NOTEBOOK_EDIT = "NotebookEdit"
    """Edit Jupyter notebook cells."""

    NOTEBOOK_READ = "NotebookRead"
    """Read Jupyter notebook cells and outputs."""

    # Task management
    TASK_CREATE = "TaskCreate"
    """Create a new task in the task list."""

    TASK_GET = "TaskGet"
    """Get task details by ID."""

    TASK_UPDATE = "TaskUpdate"
    """Update an existing task."""

    TASK_LIST = "TaskList"
    """List all tasks in the task list."""

    TASK_STOP = "TaskStop"
    """Stop a running background task."""

    TASK_OUTPUT = "TaskOutput"
    """Get output from a task."""

    # User interaction
    ASK_USER_QUESTION = "AskUserQuestion"
    """Ask the user a clarifying question."""

    # Plan mode
    ENTER_PLAN_MODE = "EnterPlanMode"
    """Enter plan mode for complex tasks."""

    EXIT_PLAN_MODE = "ExitPlanMode"
    """Exit plan mode after planning is complete."""

    # Skills
    SKILL = "Skill"
    """Invoke a skill within the conversation."""

    # MCP (Model Context Protocol)
    MCP = "Mcp"
    """MCP tool invocation (sentinel for mcp__* prefix pattern).

    Note: This is a sentinel value, not an exact API match. MCP tools have
    dynamic names like 'mcp__linear-server__list_issues'. The from_string()
    method handles prefix matching. Value uses PascalCase for consistency
    with other enum values.
    """

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

        Note:
            Matching is case-sensitive. "Read" matches READ, but "read" returns
            UNKNOWN. This matches the exact tool names from Claude Code API.
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
        return tool in {cls.READ, cls.WRITE, cls.EDIT, cls.LS}

    @classmethod
    def is_search_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a search operation."""
        return tool in {cls.GLOB, cls.GREP}

    @classmethod
    def is_execution_tool(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is an execution tool."""
        return tool in {cls.BASH, cls.BASH_OUTPUT, cls.TASK, cls.KILL_SHELL}

    @classmethod
    def is_web_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a web operation."""
        return tool in {cls.WEB_FETCH, cls.WEB_SEARCH}

    @classmethod
    def is_task_management(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a task management tool."""
        return tool in {
            cls.TASK_CREATE,
            cls.TASK_GET,
            cls.TASK_UPDATE,
            cls.TASK_LIST,
            cls.TASK_STOP,
            cls.TASK_OUTPUT,
        }

    @classmethod
    def is_notebook_operation(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a notebook operation."""
        return tool in {cls.NOTEBOOK_EDIT, cls.NOTEBOOK_READ}

    @classmethod
    def is_user_interaction(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a user interaction tool."""
        return tool == cls.ASK_USER_QUESTION

    @classmethod
    def is_plan_mode(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is a plan mode tool."""
        return tool in {cls.ENTER_PLAN_MODE, cls.EXIT_PLAN_MODE}

    @classmethod
    def is_skill(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is the Skill tool."""
        return tool == cls.SKILL

    @classmethod
    def is_mcp_tool(cls, tool: EnumClaudeCodeToolName) -> bool:
        """Check if the tool is an MCP tool."""
        return tool == cls.MCP


__all__ = ["EnumClaudeCodeToolName"]
