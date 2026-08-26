# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operating mode declared in ``~/.onex/config.yaml``.

Mode A ("local") runs ONEX with no cloud dependency. Mode B ("cloud") is the
cloud-connected posture the connect-cloud onboarding flow provisions.
"""

from enum import Enum, unique

# Legacy alias emitted by pre-OMN-16037 ``onex config init``. The old writer
# called Mode A "standalone"; the surviving schema calls it "local". Same
# concept, so the value is silently migrated rather than rejected.
LEGACY_MODE_ALIASES: dict[str, str] = {"standalone": "local"}


@unique
class EnumUserConfigMode(str, Enum):
    """Operating mode for a user's local ONEX installation."""

    LOCAL = "local"
    CLOUD = "cloud"


__all__ = ["LEGACY_MODE_ALIASES", "EnumUserConfigMode"]
