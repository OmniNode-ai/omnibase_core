# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A permitted lifecycle transition of a manifest (OMN-22001)."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_experiment_lifecycle_state import (
    EnumExperimentLifecycleState,
)


class ModelManifestTransition(BaseModel):
    """One edge of the experiment lifecycle the manifest permits.

    Attributes:
        from_state: State the edge leaves. Never a terminal state.
        to_state: State the edge enters.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    from_state: EnumExperimentLifecycleState
    to_state: EnumExperimentLifecycleState

    @model_validator(mode="after")
    def _no_exit_from_a_terminal_state(self) -> Self:
        if self.from_state.is_terminal:
            raise ValueError(
                f"{self.from_state.value} is a terminal state and has no exit"
            )
        return self
