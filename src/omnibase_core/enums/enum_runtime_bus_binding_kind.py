# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime bus binding kind for the ONEX runtime bus declaration."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumRuntimeBusBindingKind"]


@unique
class EnumRuntimeBusBindingKind(UtilStrValueHelper, str, Enum):
    """How the runtime bus is bound to a broker.

    Values:
        HOSTED: runtime publishes on the host's broker.
        INMEMORY_FORWARDED: runtime-local in-memory bus whose recorded events a forwarder carries to the hosted bus.
        INMEMORY_TEST: in-memory with no forwarder, declared by a test.
        INMEMORY_UNFORWARDED: in-memory declared but no forwarder available.
        UNKNOWN: no binding was declared at all.
    """

    HOSTED = "hosted"
    INMEMORY_FORWARDED = "inmemory_forwarded"
    INMEMORY_TEST = "inmemory_test"
    INMEMORY_UNFORWARDED = "inmemory_unforwarded"
    UNKNOWN = "unknown"

    @property
    def is_in_memory(self) -> bool:
        """Return True for the three INMEMORY_* members."""
        return self in {
            EnumRuntimeBusBindingKind.INMEMORY_FORWARDED,
            EnumRuntimeBusBindingKind.INMEMORY_TEST,
            EnumRuntimeBusBindingKind.INMEMORY_UNFORWARDED,
        }

    @property
    def is_degraded(self) -> bool:
        """Return True for INMEMORY_UNFORWARDED and UNKNOWN.

        The in-memory bus with no forwarder and no test declaration, events go nowhere.
        """
        return self in {
            EnumRuntimeBusBindingKind.INMEMORY_UNFORWARDED,
            EnumRuntimeBusBindingKind.UNKNOWN,
        }
