# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-ops verb allowlist loader (OMN-14168).

Resolves the bounded set of ``mutation_verb`` values a RUNTIME_OPS_READBACK
evidence receipt may carry. The allowlist is GOVERNED DATA — it lives in
``contracts/runtime_ops_verb_allowlist.yaml`` (mirroring
``test_selection_adjacency.yaml``), never hardcoded in Python — so adding or
removing a verb is a reviewable governance change, not a code edit.

Both enforcement surfaces resolve the set from here so they cannot drift:

  * :class:`omnibase_core.models.contracts.ticket.model_dod_receipt.ModelDodReceipt`
    validates ``mutation_verb`` against it, and
  * the omnimarket ``DurableEvidenceGate`` RUNTIME_OPS_READBACK branch (G2b).

The result is cached per-process (``functools.cache``) so the bundled YAML is
read at most once; callers get a frozenset for cheap membership checks.
"""

from __future__ import annotations

import importlib.resources
from functools import cache
from pathlib import Path

import yaml

_CONTRACTS_PKG = "omnibase_core.contracts"
_ALLOWLIST_YAML = "runtime_ops_verb_allowlist.yaml"
_ALLOWLIST_KEY = "runtime_ops_verbs"


@cache
def load_runtime_ops_verb_allowlist() -> frozenset[str]:
    """Return the governed runtime-ops ``mutation_verb`` allowlist.

    Reads ``contracts/runtime_ops_verb_allowlist.yaml`` via
    ``importlib.resources`` so it resolves both in a source checkout and in an
    installed wheel. Result is cached for the process.

    Raises:
        FileNotFoundError: the bundled allowlist YAML is missing (fatal config
            error — the class cannot be enforced without its governed data).
        ValueError: the YAML exists but does not declare a non-empty
            ``runtime_ops_verbs`` list of strings.
    """
    try:
        ref = importlib.resources.files(_CONTRACTS_PKG) / _ALLOWLIST_YAML
        raw = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError) as exc:
        fallback = Path(__file__).parent.parent / "contracts" / _ALLOWLIST_YAML
        if fallback.exists():
            raw = fallback.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(  # error-ok: bundled governed YAML missing — fatal config error
                f"Cannot locate {_ALLOWLIST_YAML}; tried importlib.resources "
                f"and {fallback}"
            ) from exc

    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(
            f"{_ALLOWLIST_YAML} must be a mapping with a {_ALLOWLIST_KEY!r} key"
        )
    verbs = data.get(_ALLOWLIST_KEY)
    if not isinstance(verbs, list) or not verbs:
        raise ValueError(
            f"{_ALLOWLIST_YAML} must declare a non-empty {_ALLOWLIST_KEY!r} list"
        )
    normalized: set[str] = set()
    for verb in verbs:
        if not isinstance(verb, str) or not verb.strip():
            raise ValueError(
                f"{_ALLOWLIST_KEY} entries must be non-blank strings, got: {verb!r}"
            )
        normalized.add(verb.strip())
    return frozenset(normalized)


__all__ = ["load_runtime_ops_verb_allowlist"]
