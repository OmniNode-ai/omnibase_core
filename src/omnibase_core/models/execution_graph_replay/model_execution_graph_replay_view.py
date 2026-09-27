# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Public execution graph read model, separating replay, labels, annotations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.execution_graph_replay.model_execution_graph_annotations import (
    ModelExecutionGraphAnnotations,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_label import (
    ModelExecutionGraphLabel,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_replay import (
    ModelExecutionGraphReplay,
)


class ModelExecutionGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    replay: ModelExecutionGraphReplay
    labels: tuple[ModelExecutionGraphLabel, ...]
    annotations: ModelExecutionGraphAnnotations
