# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract normalizer functions (parent epic OMN-9757).

Canonical migration-audit layer for legacy contract YAML. Each function is a
pure ``dict -> dict`` transform that derives a single canonical contract field
from an older corpus shape so the strict typed models can validate it. The
layer is invoked deliberately by the migration_audit validator mode and the
batch-validator CLI (Task 11/12, OMN-9768/9769) -- never by the runtime read
path.

Architecturally settled in OMN-9757: canonical models stay
``extra="forbid"``; corpus is classified before validation; per-family
normalization is explicit, versioned, and logged. These transforms are not
deprecated bridges or backwards-compatibility shims for live code -- they are
the audit-mode entry point that lets the platform inventory legacy contracts
without loosening the canonical schema. Dropped or rewritten content is the
caller's responsibility to preserve elsewhere.

Functions in this module:
    - strip_legacy_metadata (OMN-9761): drops the legacy ``metadata`` block
      and the duplicate ``contract_name`` / ``node_name`` aliases.
    - normalize_event_bus (OMN-9762, family_legacy_event_bus): strips the
      legacy event_bus block and top-level topic list keys.
    - normalize_io_model_ref (OMN-9763): converts dict-shaped
      ``input_model`` / ``output_model`` refs to dotted-string form.
    - normalize_handler_routing (OMN-9764): derives canonical
      handler-routing fields from legacy handler declarations.
    - normalize_omnimarket_v0_contract (OMN-9765): strips legacy omnimarket
      v0 handler, descriptor, and terminal_event blocks while hoisting
      handler.input_model when needed.
    - normalize_dod_evidence (OMN-9766): maps legacy ``kind`` → ``type``
      on dod_evidence entries.
    - compose_normalization_pipeline (OMN-9766): composes the six
      normalizers in the documented order.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import cast

from omnibase_core.types.type_json import JsonType

_LEGACY_METADATA_KEYS: frozenset[str] = frozenset(
    {"metadata", "contract_name", "node_name"}
)

_LEGACY_EVENT_BUS_KEYS: frozenset[str] = frozenset(
    {"event_bus", "subscribe_topics", "publish_topics", "topics"}
)

_DEFAULT_HANDLER_ROUTING_VERSION: dict[str, int] = {"major": 1, "minor": 0, "patch": 0}
_MULTI_OP_FLAG: str = "multi_operation_requires_human_review"

_PASCAL_TO_SNAKE_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_PASCAL_TO_SNAKE_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")


def strip_legacy_metadata(raw: Mapping[str, object]) -> dict[str, object]:
    """Drop legacy top-level metadata fields from a contract dict.

    Removes exactly three keys if present: ``metadata``, ``contract_name``,
    and ``node_name``. The legacy ``metadata`` block (description, author,
    etc.) and the duplicate ``contract_name`` / ``node_name`` aliases were
    superseded by the canonical schema, which uses the top-level ``name``
    field as the single identifier.

    Args:
        raw: parsed contract YAML as a dict.

    Returns:
        A new dict with the legacy keys filtered out. The input is never
        mutated; canonical keys (including ``name`` and ``node_type``)
        are passed through unchanged.

    Note:
        This is a compatibility strip. The dropped ``metadata`` block is
        not preserved into the canonical representation; capture it from
        the raw dict before calling this function if it must be retained.
    """
    return {k: v for k, v in raw.items() if k not in _LEGACY_METADATA_KEYS}


def _normalize_single_io_ref(value: dict[str, object] | str | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    module = value.get("module")
    name = value.get("name")
    if isinstance(module, str) and isinstance(name, str) and module and name:
        return f"{module}.{name}"
    return None


def normalize_event_bus(raw: dict[str, JsonType]) -> dict[str, JsonType]:
    """Strip the legacy event_bus block and top-level topic list keys.

    Drops `event_bus`, `subscribe_topics`, `publish_topics`, and `topics` keys
    from the raw contract dict so the remainder passes canonical
    extra="forbid" validation. Returns a new dict; does not mutate the input.
    Idempotent on dicts that already lack these keys.

    The event-bus declarations are preserved separately by callers that need
    them (e.g., into a typed ModelEventBusConfig); this function only removes
    the keys that would otherwise fail validation.
    """
    return {k: v for k, v in raw.items() if k not in _LEGACY_EVENT_BUS_KEYS}


def normalize_io_model_ref(raw: dict[str, object]) -> dict[str, object]:
    """Convert dict-shaped ``input_model``/``output_model`` refs to strings.

    Legacy contracts often expressed model references as
    ``{"name": "ModelFooRequest", "module": "foo.bar.models"}``. The canonical
    typed contract model expects a single dotted string
    ``"foo.bar.models.ModelFooRequest"``.

    Behavior:
    - ``{name: X, module: Y}`` -> ``"Y.X"``
    - String passthrough unchanged
    - Missing field not injected
    - Incomplete dict refs preserved
    - Does not mutate input; idempotent
    """
    result = dict(raw)
    for field in ("input_model", "output_model"):
        if field not in result:
            continue
        value = result[field]
        if value is None or isinstance(value, (str, dict)):
            normalized = _normalize_single_io_ref(value)
            if normalized is not None:
                result[field] = normalized
    return result


def _pascal_to_snake(name: str) -> str:
    s1 = _PASCAL_TO_SNAKE_BOUNDARY_1.sub(r"\1_\2", name)
    return _PASCAL_TO_SNAKE_BOUNDARY_2.sub(r"\1_\2", s1).lower()


def normalize_handler_routing(raw: dict[str, object]) -> dict[str, object]:
    """Normalize legacy ``handler_routing`` block to canonical subcontract shape.

    Adds the default version, derives ``routing_key`` from
    ``supported_operations``/``handler_type``, and derives ``handler_key`` by
    snake-casing ``handler.name``. Multi-op handlers receive
    ``_normalization_flag = "multi_operation_requires_human_review"`` because
    picking ``ops[0]`` as the routing key is a synthetic guess.

    No-op when ``handler_routing`` is absent. Input is never mutated.
    """
    if "handler_routing" not in raw:
        return raw

    result = copy.deepcopy(raw)
    hr = result["handler_routing"]
    if not isinstance(hr, dict):
        return result

    if "version" not in hr:
        hr["version"] = dict(_DEFAULT_HANDLER_ROUTING_VERSION)

    raw_handlers = hr.get("handlers", [])
    if not isinstance(raw_handlers, list):
        return result

    normalized_handlers: list[object] = []
    for h in raw_handlers:
        if not isinstance(h, dict):
            normalized_handlers.append(h)
            continue
        nh: dict[str, object] = dict(h)
        if "routing_key" not in nh:
            ops_raw = nh.get("supported_operations", [])
            ops = ops_raw if isinstance(ops_raw, list) else []
            if len(ops) == 1:
                nh["routing_key"] = ops[0]
            elif len(ops) > 1:
                nh["routing_key"] = ops[0]
                nh["_normalization_flag"] = _MULTI_OP_FLAG
            elif "handler_type" in nh:
                nh["routing_key"] = nh["handler_type"]
        if "handler_key" not in nh:
            nested = nh.get("handler", {})
            name = nested.get("name", "") if isinstance(nested, dict) else ""
            if isinstance(name, str) and name:
                nh["handler_key"] = _pascal_to_snake(name)
        normalized_handlers.append(nh)
    hr["handlers"] = normalized_handlers
    return result


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

    Compatibility-stripping transform, not a semantic migration. The
    ``handler``, ``descriptor``, and ``terminal_event`` blocks are dropped
    entirely; ``descriptor.node_archetype``, ``descriptor.timeout_ms``,
    and the ``terminal_event`` topic string are not carried forward.
    Callers that need this information must extract it before running
    the normalizer.

    The only field salvaged is ``handler.input_model``, which is hoisted
    to a root-level ``input_model`` when not already present.
    """
    result = copy.deepcopy(raw)
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


_DOD_KIND_TO_TYPE: dict[str, str] = {
    "test": "unit_test",
    "unit_test": "unit_test",
    "integration_test": "integration_test",
    "pr_merged": "pr_merged",
    "file_exists": "file_exists",
}


def normalize_dod_evidence(raw: dict[str, object]) -> dict[str, object]:
    """Map legacy ``kind`` → ``type`` on dod_evidence entries.

    Legacy contracts spelled the discriminator on each dod_evidence entry
    as ``kind``; the canonical schema names it ``type``. Per-entry rules:

    - String entries (``"test_passes"``) pass through unchanged.
    - Dict entries with ``kind`` and no ``type`` are rewritten:
      ``kind`` is removed, ``type`` is set via :data:`_DOD_KIND_TO_TYPE`
      (or copied verbatim if no mapping is registered).
    - Dict entries that already carry ``type`` are left alone (no double
      mapping; pre-canonical entries win).

    The input dict is not mutated; a new dict is returned. Idempotent:
    running twice yields the same result. No-op when ``dod_evidence`` is
    absent.

    Corpus context: 8 files in the audited corpus carry legacy ``kind``.
    """
    if "dod_evidence" not in raw:
        return raw
    result = dict(raw)
    items_raw = result.get("dod_evidence")
    if not isinstance(items_raw, list):
        return result
    new_items: list[object] = []
    for item in items_raw:
        if isinstance(item, dict) and "kind" in item and "type" not in item:
            normalized: dict[str, object] = dict(item)
            kind_value = normalized.pop("kind")
            if isinstance(kind_value, str):
                normalized["type"] = _DOD_KIND_TO_TYPE.get(kind_value, kind_value)
            new_items.append(normalized)
        else:
            new_items.append(item)
    result["dod_evidence"] = new_items
    return result


def compose_normalization_pipeline(raw: dict[str, object]) -> dict[str, object]:
    """Apply all per-family normalizers in canonical order.

    Step order is fixed and documented:

    1. :func:`strip_legacy_metadata` — drop ``metadata`` /
       ``contract_name`` / ``node_name``.
    2. :func:`normalize_event_bus` — strip the legacy event_bus block
       and top-level topic keys.
    3. :func:`normalize_io_model_ref` — convert ``{name, module}`` dict
       refs to dotted strings.
    4. :func:`normalize_handler_routing` — derive routing_key /
       handler_key / version on the routing block.
    5. :func:`normalize_omnimarket_v0_contract` — conditional on
       :func:`is_omnimarket_v0`; rewrites the omnimarket v0 shape.
    6. :func:`normalize_dod_evidence` — map legacy ``kind`` → ``type``.

    Pure: no I/O, no logging, no mutation of the caller's dict. Note
    that :func:`normalize_event_bus` is typed against ``dict[str,
    JsonType]``; we cast at the boundary because the pipeline carries
    unconstrained ``dict[str, object]``.

    Task 14 will append ``normalize_misc_extra_fields`` as the final
    step; that step is intentionally deferred per OMN-9757 plan.
    """
    out: dict[str, object] = strip_legacy_metadata(raw)
    out = cast(
        "dict[str, object]",
        normalize_event_bus(cast("dict[str, JsonType]", out)),
    )
    out = normalize_io_model_ref(out)
    out = normalize_handler_routing(out)
    if is_omnimarket_v0(out):
        out = normalize_omnimarket_v0_contract(out)
    out = normalize_dod_evidence(out)
    return out


__all__ = [
    "compose_normalization_pipeline",
    "is_omnimarket_v0",
    "normalize_dod_evidence",
    "normalize_event_bus",
    "normalize_handler_routing",
    "normalize_io_model_ref",
    "normalize_omnimarket_v0_contract",
    "strip_legacy_metadata",
]
