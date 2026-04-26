# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract normalizer functions (OMN-9761, OMN-9763).

Each function in this module is a pure dict→dict transform that takes a
raw legacy contract dict (parsed YAML) and returns a new dict closer to
the canonical schema. They are intentionally narrow — one migration
family per function — so they can be composed into a pipeline and
audited independently.

These are compatibility-stripping helpers, not semantic-preserving
migrations. Content that is dropped here (e.g. ``metadata.author``)
must be captured by the caller before normalization runs if it needs
to be retained.
"""

from __future__ import annotations

from collections.abc import Mapping

_LEGACY_METADATA_KEYS: frozenset[str] = frozenset(
    {"metadata", "contract_name", "node_name"}
)


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


def normalize_io_model_ref(raw: dict[str, object]) -> dict[str, object]:
    """Convert dict-shaped ``input_model``/``output_model`` refs to dotted-string canonical form.

    Legacy contracts often expressed model references as
    ``{"name": "ModelFooRequest", "module": "foo.bar.models"}``. The canonical
    typed contract model expects a single dotted string ``"foo.bar.models.ModelFooRequest"``.

    Behavior:
    - ``{name: X, module: Y}`` -> ``"Y.X"``
    - String passthrough unchanged
    - Missing field not injected
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
