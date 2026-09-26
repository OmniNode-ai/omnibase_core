# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Canonical model for rendered template output.
"""

from pydantic import BaseModel, ConfigDict


class ModelRenderedTemplate(BaseModel):
    """
    Canonical model for rendered template output.
    """

    model_config = ConfigDict(extra="forbid")

    content: str
