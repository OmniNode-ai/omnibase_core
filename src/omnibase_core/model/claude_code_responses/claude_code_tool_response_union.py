# Generated from contract: tool_claude_code_response_models v1.0.0
"""Union type for all Claude Code tool responses with discriminated union support."""

from typing import Union

from pydantic import BaseModel, Field

from .model_bash_tool_response import ModelBashToolResponse
from .model_edit_tool_response import ModelEditToolResponse
from .model_glob_tool_response import ModelGlobToolResponse
from .model_grep_tool_response import ModelGrepToolResponse
from .model_ls_tool_response import ModelLSToolResponse
from .model_multi_edit_tool_response import ModelMultiEditToolResponse
from .model_notebook_edit_tool_response import ModelNotebookEditToolResponse
from .model_read_tool_response import ModelReadToolResponse
from .model_web_fetch_tool_response import ModelWebFetchToolResponse
from .model_web_search_tool_response import ModelWebSearchToolResponse
from .model_write_tool_response import ModelWriteToolResponse


def get_tool_name_discriminator(v: dict) -> str:
    """Extract tool name from response for discriminated union."""
    if isinstance(v, dict):
        # Try to determine tool type from response structure
        if "exit_code" in v and "stdout" in v:
            return "bash"
        if "content" in v and "file_path" in v and "lines_read" in v:
            return "read"
        if "bytes_written" in v and "operation_type" in v:
            return "write"
        if "old_string" in v and "new_string" in v and "replacements_made" in v:
            return "edit"
        if "pattern" in v and "search_results" in v:
            return "grep"
        if (
            "pattern" in v
            and "matches_found" in v
            and isinstance(v.get("matches_found"), list)
        ):
            return "glob"
        if "entries" in v and "directories_count" in v:
            return "ls"
        if "edits_applied" in v and "total_edits" in v:
            return "multiedit"
        if "query" in v and "search_engine" in v:
            return "websearch"
        if "url" in v and "status_code" in v:
            return "webfetch"
        if "notebook_path" in v and "edit_mode" in v:
            return "notebookedit"

    # Fallback to empty string if can't determine
    return "unknown"


# ONEX-compliant Union of all Claude Code tool responses
ClaudeCodeToolResponseUnion = Union[
    ModelBashToolResponse,
    ModelReadToolResponse,
    ModelWriteToolResponse,
    ModelEditToolResponse,
    ModelGrepToolResponse,
    ModelGlobToolResponse,
    ModelLSToolResponse,
    ModelMultiEditToolResponse,
    ModelWebSearchToolResponse,
    ModelWebFetchToolResponse,
    ModelNotebookEditToolResponse,
    dict,  # Fallback for unrecognized tool responses
    str,  # Fallback for simple string responses
    int,  # Fallback for numeric responses
    float,  # Fallback for floating point responses
    bool,  # Fallback for boolean responses
    list,  # Fallback for array responses
    None,  # Fallback for null responses
]


class ModelClaudeCodeResponseWrapper(BaseModel):
    """Wrapper for Claude Code tool responses with tool identification."""

    tool_name: str = Field(
        ...,
        description="Name of the tool that generated this response",
    )
    response: ClaudeCodeToolResponseUnion = Field(
        ...,
        description="The actual tool response data",
    )

    class Config:
        extra = "forbid"

    @classmethod
    def create_bash_response(
        cls,
        response: ModelBashToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Bash tool response."""
        return cls(tool_name="bash", response=response)

    @classmethod
    def create_read_response(
        cls,
        response: ModelReadToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Read tool response."""
        return cls(tool_name="read", response=response)

    @classmethod
    def create_write_response(
        cls,
        response: ModelWriteToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Write tool response."""
        return cls(tool_name="write", response=response)

    @classmethod
    def create_edit_response(
        cls,
        response: ModelEditToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Edit tool response."""
        return cls(tool_name="edit", response=response)

    @classmethod
    def create_grep_response(
        cls,
        response: ModelGrepToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Grep tool response."""
        return cls(tool_name="grep", response=response)

    @classmethod
    def create_glob_response(
        cls,
        response: ModelGlobToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for Glob tool response."""
        return cls(tool_name="glob", response=response)

    @classmethod
    def create_ls_response(
        cls,
        response: ModelLSToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for LS tool response."""
        return cls(tool_name="ls", response=response)

    @classmethod
    def create_multiedit_response(
        cls,
        response: ModelMultiEditToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for MultiEdit tool response."""
        return cls(tool_name="multiedit", response=response)

    @classmethod
    def create_websearch_response(
        cls,
        response: ModelWebSearchToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for WebSearch tool response."""
        return cls(tool_name="websearch", response=response)

    @classmethod
    def create_webfetch_response(
        cls,
        response: ModelWebFetchToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for WebFetch tool response."""
        return cls(tool_name="webfetch", response=response)

    @classmethod
    def create_notebookedit_response(
        cls,
        response: ModelNotebookEditToolResponse,
    ) -> "ModelClaudeCodeResponseWrapper":
        """Create wrapper for NotebookEdit tool response."""
        return cls(tool_name="notebookedit", response=response)
