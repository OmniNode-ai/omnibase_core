# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Match rules of the emits check, read from validator-requirements.yaml (OMN-22003).

The consumer holds no pattern of its own: how a pre-commit entry names its
module, which package counts as core, and which marker in that module's source
shows it writes through the report writer are spec data.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRequirementEmitsCheck"]


class ModelValidatorRequirementEmitsCheck(BaseModel):
    """The spec's top-level ``emits_check`` block."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module_pattern: str = Field(
        description=(
            "Regex with one group that captures the dotted module a pre-commit "
            "entry runs with python -m."
        )
    )
    core_package: str = Field(
        description="Top-level package whose runtimes count as core-format."
    )
    writer_marker: str = Field(
        description="Text a core-format runtime's source holds when it writes through the report writer."
    )
