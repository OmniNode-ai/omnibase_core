# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Re-export of the runtime-ops verb allowlist loader (OMN-14168).

The canonical implementation was relocated to
:mod:`omnibase_core.utils.util_runtime_ops_verb_loader` under OMN-14331 so that
``omnibase_core.models.contracts.ticket.model_dod_receipt`` (a MODEL) can import
the loader without crossing the ``models -> validation`` layering back-edge the
import-linter oracle forbids (epic OMN-3210).

The loader is pure governed-data I/O with no model dependencies. This module is
kept as a stable import site for cross-repo consumers (omnimarket's
``DurableEvidenceGate`` and ``node_linear_triage``) that resolve the allowlist
via ``omnibase_core.validation.runtime_ops_verb_loader``.
"""

from omnibase_core.utils.util_runtime_ops_verb_loader import (
    load_runtime_ops_verb_allowlist,
)

__all__ = ["load_runtime_ops_verb_allowlist"]
