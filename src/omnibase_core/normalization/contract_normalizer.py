# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract normalizer (parent epic OMN-9757).

Pure dict→dict transforms that rewrite legacy contract shapes into the
canonical representation. Each function targets a single migration
family. Functions never mutate their input.
"""

from __future__ import annotations

import copy as _copy


def is_omnimarket_v0(raw: dict[str, object]) -> bool:
    """Return True iff ``raw`` carries the omnimarket v0 contract shape.

    The v0 shape is identified by a top-level ``handler`` dict that
    declares a ``class`` field. This is the legacy shape used by the
    82-file omnimarket cohort prior to the canonical contract layout.
    """
    handler = raw.get("handler")
    return isinstance(handler, dict) and "class" in handler


def normalize_omnimarket_v0_contract(raw: dict[str, object]) -> dict[str, object]:
    """Rewrite an omnimarket v0 contract dict to the canonical shape.

    Compatibility-stripping transform — NOT a semantic migration. The
    ``handler``, ``descriptor``, and ``terminal_event`` blocks are dropped
    entirely; ``descriptor.node_archetype``, ``descriptor.timeout_ms``,
    and the ``terminal_event`` topic string are NOT carried forward.
    Callers that need this information must extract it before running
    the normalizer.

    The only field salvaged is ``handler.input_model``, which is hoisted
    to a root-level ``input_model`` when not already present.
    """
    result = _copy.deepcopy(raw)
    handler_block = result.pop("handler", None)
    result.pop("descriptor", None)
    result.pop("terminal_event", None)
    if (
        isinstance(handler_block, dict)
        and "input_model" in handler_block
        and "input_model" not in result
    ):
        result["input_model"] = handler_block["input_model"]
    return result
