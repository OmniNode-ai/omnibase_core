# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumBackendFindingReason: why auto-configuration skipped an entry point."""

from enum import Enum, unique


@unique
class EnumBackendFindingReason(str, Enum):
    """Reason an ``onex.backends`` entry point was not used.

    States:
        LOAD_FAILED: the entry point could not be imported
        NO_PROBE: the loaded object has no ``probe()``
        PROBE_RAISED: ``probe()`` raised instead of returning a result
        NOT_INSTANTIABLE: the authoritative backend could not be constructed
        UNKNOWN_PROTOCOL: the probed protocol has no interface the registry knows
    """

    LOAD_FAILED = "load_failed"
    NO_PROBE = "no_probe"
    PROBE_RAISED = "probe_raised"
    NOT_INSTANTIABLE = "not_instantiable"
    UNKNOWN_PROTOCOL = "unknown_protocol"
