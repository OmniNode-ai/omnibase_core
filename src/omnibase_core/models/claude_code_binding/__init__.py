# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Claude Code binding install contract models (OMN-18531; relocated from omnimarket by OMN-21093).

The install wire family — the binding row, its enums and arguments, and the
install request/result — moved here from omnimarket so the shared models sit
below the node boundary: omnibase_infra's skill mapping names
ModelBindingInstallResult, and a cross-repo reference into an omnimarket
node package is a seam the node-boundary gate refuses (OMN-17427/OMN-20703).
omnimarket re-exports these classes from their former module paths.
"""

from omnibase_core.enums.enum_binding_kind import (
    EnumBindingKind,
)
from omnibase_core.enums.enum_client_max_mode import (
    EnumClientMaxMode,
)
from omnibase_core.enums.enum_client_verdict_action import (
    EnumClientVerdictAction,
)
from omnibase_core.models.claude_code_binding.model_binding_install_request import (
    ModelBindingInstallRequest,
)
from omnibase_core.models.claude_code_binding.model_binding_install_result import (
    ModelBindingInstallResult,
)
from omnibase_core.models.claude_code_binding.model_client_argument import (
    ModelClientArgument,
)
from omnibase_core.models.claude_code_binding.model_client_binding import (
    ModelClientBinding,
)

__all__ = [
    "EnumBindingKind",
    "EnumClientMaxMode",
    "EnumClientVerdictAction",
    "ModelBindingInstallRequest",
    "ModelBindingInstallResult",
    "ModelClientArgument",
    "ModelClientBinding",
]
