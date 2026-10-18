# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The strict repository policy has only explicit reasoned exceptions."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.readme_only_docs.model_documentation_exception import (
    ModelDocumentationException,
)


class ModelDocumentationPolicy(BaseModel):
    """No implicit legacy allowlist, advisory mode or repository exemption flag."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    exceptions: tuple[ModelDocumentationException, ...] = ()
