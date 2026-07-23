# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deprecated re-export shim for UtilStrValueHelper (OMN-14959).

The canonical definition moved to
``omnibase_core.enums.enum_str_enum_base`` — the base class of every
string enum belongs inside the ``enums`` foundation package so it is
self-contained under the ``core-foundation-no-upward`` import-linter
contract (OMN-3210). This module is a pure re-export shim retained for
non-foundation and cross-repo importers; ``utils -> enums`` is
downward-legal and uncontracted, so this shim is not itself a layering
violation. Shim burn-down is tracked as follow-up scope, not this ticket.

See Also:
    - omnibase_core.enums.enum_str_enum_base: canonical definition
    - omnibase_compat.utils.util_str_enum_base: equivalent definition for compat consumers
"""

from __future__ import annotations

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["UtilStrValueHelper"]
