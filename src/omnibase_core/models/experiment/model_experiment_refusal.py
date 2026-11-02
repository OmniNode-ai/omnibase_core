# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A refusal of the experiment loop, with the experiment it concerns (OMN-22001)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from omnibase_core.enums.enum_experiment_refusal import EnumExperimentRefusal


class ModelExperimentRefusal(BaseModel):
    """The loop stopped for one experiment, and why.

    Attributes:
        experiment_id: The experiment.
        refusal: The operational refusal.
        refused_at: When the loop refused.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    refusal: EnumExperimentRefusal
    refused_at: AwareDatetime
