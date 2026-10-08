# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed projection of producer job ids from GitHub Actions workflow YAML."""

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict


class ModelRequiredContextProducerWorkflowFields(BaseModel):
    """Require a jobs mapping while leaving GitHub's other workflow fields alone."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    jobs: dict[str, object]

    @classmethod
    def from_yaml(cls, text: str) -> Self:
        """Parse YAML text and validate the jobs projection, without I/O."""
        document: object = yaml.safe_load(text)
        if isinstance(document, dict):
            return cls.model_validate({"jobs": document.get("jobs")})
        return cls.model_validate(document)
