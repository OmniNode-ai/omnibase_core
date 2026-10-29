# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeTree -- facts read from one revision of a repository (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)


class ModelCanonicalFileShapeTree(BaseModel):
    """What the shape rules need to know about one revision.

    The reader fills every field from git and the rule parameters; the checker
    never touches the filesystem. ``shebang_lines`` hold the first line of each
    extensionless file that starts with the shebang prefix, ``handler_class_paths`` and
    ``argparse_main_paths`` are source files whose text matched the contract's
    patterns, and ``contract_texts`` hold every ``contract.yaml``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[str, ...] = Field(default_factory=tuple)
    shebang_lines: tuple[ModelCanonicalFileShapeText, ...] = Field(
        default_factory=tuple
    )
    handler_class_paths: tuple[str, ...] = Field(default_factory=tuple)
    argparse_main_paths: tuple[str, ...] = Field(default_factory=tuple)
    contract_texts: tuple[ModelCanonicalFileShapeText, ...] = Field(
        default_factory=tuple
    )
    pyproject_text: str | None = None
