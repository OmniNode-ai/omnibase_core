# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerEffectBackends: list the effect nodes that are not on both backends (OMN-22911).

Pure COMPUTE over parsed contract documents; no file, network or environment access. The rule
(plan section 3.1 and 3.6): an effect node declares in its contract

    backends:
      default: in_memory
      in_memory: {factory: <dotted path>}
      real: {factory: <dotted path>, overlay_key: <overlay key that selects it>}

An effect has an in-memory default when ``default`` is ``in_memory`` and ``in_memory.factory`` is
a non-blank string. It is on both backends when it also names a real ``factory`` and the
``overlay_key`` that chooses it.
"""

from __future__ import annotations

from omnibase_core.models.validation.model_effect_backend_entry import (
    ModelEffectBackendEntry,
)
from omnibase_core.models.validation.model_effect_backends_report import (
    ModelEffectBackendsReport,
)
from omnibase_core.models.validation.model_effect_backends_request import (
    ModelEffectBackendsRequest,
)
from omnibase_core.models.validation.model_effect_contract_document import (
    ModelEffectContractDocument,
)

EFFECT_NODE_TYPE = "effect"
DEFAULT_BACKEND = "in_memory"


def _text(mapping: object, key: str) -> str:
    if not isinstance(mapping, dict):
        return ""
    value = mapping.get(key)
    return value.strip() if isinstance(value, str) else ""


def _entry(item: ModelEffectContractDocument) -> ModelEffectBackendEntry:
    backends = item.document.get("backends")
    name = _text(item.document, "node_name") or _text(item.document, "name")
    in_memory = backends.get("in_memory") if isinstance(backends, dict) else None
    real = backends.get("real") if isinstance(backends, dict) else None
    return ModelEffectBackendEntry(
        node_name=name or item.path,
        path=item.path,
        has_in_memory_default=_text(backends, "default") == DEFAULT_BACKEND
        and bool(_text(in_memory, "factory")),
        has_real_backend_overlay=bool(_text(real, "factory"))
        and bool(_text(real, "overlay_key")),
        in_memory_factory=_text(in_memory, "factory"),
        real_factory=_text(real, "factory"),
        overlay_key=_text(real, "overlay_key"),
        scenario=_text(
            backends.get("suite") if isinstance(backends, dict) else None, "scenario"
        ),
    )


class HandlerEffectBackends:
    """Judge every effect contract against the two-backend rule."""

    def handle(self, request: ModelEffectBackendsRequest) -> ModelEffectBackendsReport:
        entries = sorted(
            (
                _entry(item)
                for item in request.contracts
                if _text(item.document, "node_type") == EFFECT_NODE_TYPE
            ),
            key=lambda e: (e.node_name, e.path),
        )
        listed = tuple(entries)
        not_on_both = tuple(e.node_name for e in listed if not e.on_both)
        return ModelEffectBackendsReport(
            entries=listed,
            unreadable=tuple(sorted(request.unreadable)),
            effects_total=len(listed),
            without_in_memory_default=tuple(
                e.node_name for e in listed if not e.has_in_memory_default
            ),
            not_on_both=not_on_both,
            on_both=tuple(e.node_name for e in listed if e.on_both),
            not_on_both_count=len(not_on_both),
        )
