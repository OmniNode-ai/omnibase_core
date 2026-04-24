# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumModelRoutingBackend: model-routing substrate selector (OMN-9623).

Only meaningful when EnumInvocationKind == MODEL. Part 2 (Bifrost integration
under node_llm_inference_effect) consumes this; Part 1 defines it so the
reducer's command envelope is typed end-to-end from day one.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumModelRoutingBackend(StrValueHelper, str, Enum):
    """Enumeration of model-routing backends.

    Classifies the internal routing substrate used when dispatching a
    MODEL invocation. Only meaningful when invocation_kind == MODEL.

    Values:
        BIFROST: Internal Bifrost routing layer (Part 2 integration).
        DIRECT: Direct endpoint call with no routing middleware.
        OPENAI_COMPAT: OpenAI-compatible endpoint passthrough.
    """

    BIFROST = "BIFROST"
    DIRECT = "DIRECT"
    OPENAI_COMPAT = "OPENAI_COMPAT"


__all__ = ["EnumModelRoutingBackend"]
