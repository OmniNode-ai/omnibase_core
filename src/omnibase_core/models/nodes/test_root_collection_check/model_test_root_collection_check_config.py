# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The original infra validator's typed standalone registration table."""

from pydantic import BaseModel, ConfigDict, Field


class ModelTestRootCollectionCheckConfig(BaseModel):
    """Existing registrations and debt, supplied explicitly to COMPUTE."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    standalone_projects: dict[str, str] = Field(
        default_factory=lambda: {
            "scripts/deploy-agent": ".github/workflows/deploy-agent-tests.yml"
        }
    )
    known_uncollected_debt: tuple[str, ...] = ()
