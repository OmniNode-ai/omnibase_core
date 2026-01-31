"""Discovery configuration for cross-repo validation scanning.

Defines what files to scan during validation, including inclusion/exclusion
patterns and language mode settings.

Related ticket: OMN-1771
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationDiscoveryConfig(BaseModel):
    """Configuration for what to scan during cross-repo validation.

    Controls file discovery, exclusions, and language modes.
    Explicit configuration prevents magic path assumptions.

    Note: This is distinct from ModelDiscoveryConfig in models/discovery/
    which is for tool discovery. This config is specifically for validation scanning.

    Example:
        >>> config = ModelValidationDiscoveryConfig(
        ...     include_globs=["**/*.py", "**/*.yaml"],
        ...     exclude_globs=["**/test_*.py", "**/conftest.py"],
        ...     contract_roots=["config/contracts/"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    include_globs: tuple[str, ...] = Field(
        default=("**/*.py",),
        description="Glob patterns for files to include in validation",
    )

    exclude_globs: tuple[str, ...] = Field(
        default=(),
        description="Glob patterns for files to exclude from validation",
    )

    contract_roots: tuple[str, ...] = Field(
        default=(),
        description="Explicit paths to contract directories (no magic discovery)",
    )

    language_mode: Literal["python", "polyglot"] = Field(
        default="python",
        description="Language mode for validation",
    )

    skip_generated: bool = Field(
        default=True,
        description="Whether to skip files marked as auto-generated",
    )

    generated_markers: tuple[str, ...] = Field(
        default=("# AUTO-GENERATED", "# DO NOT EDIT"),
        description="Comment markers that indicate generated code",
    )


__all__ = ["ModelValidationDiscoveryConfig"]
