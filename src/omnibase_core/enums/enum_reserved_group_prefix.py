# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reserved consumer-group prefixes authorized by the MSK IAM policy.

Most consumer groups are *identity-derived*: ``compute_consumer_group_id`` renders
``{env}.{service}.{node_name}.{purpose}.{version}``, which is authorized because the
leading environment token matches an entry in the pinned pattern set
(``omnibase_core/contracts/consumer_group_iam_patterns.yaml``).

A small number of lanes are not identity-derived — they own a reserved prefix in the
IAM policy directly (pattern-B broker command dispatch, the phase-5 MSK smoke lane,
the runtime-config ingress lane). Those lanes mint names through
:func:`omnibase_core.event_bus.util_consumer_group.derive_prefixed_group_id` with a member
of :class:`EnumReservedGroupPrefix`, so the prefix is a declared constant rather than
an ad-hoc string literal.

.. versionadded:: OMN-15639
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumReservedGroupPrefix(UtilStrValueHelper, str, Enum):
    """Consumer-group prefixes reserved directly in the MSK IAM pattern set.

    Each member's value is the prefix WITHOUT its trailing separator. The separator
    is supplied by :meth:`separator` and is load-bearing: the IAM glob
    ``pattern-b-broker-*`` requires the trailing ``-``, so the bare prefix
    ``pattern-b-broker`` is NOT authorized. This is why
    ``derive_prefixed_group_id`` refuses to render a scope-less name.

    Attributes:
        PATTERN_B_BROKER: Pattern-B broker command-dispatch groups
            (IAM glob ``pattern-b-broker-*``).
        PHASE5_MSK_SMOKE: Phase-5 MSK connectivity smoke lane
            (IAM glob ``phase5-msk-smoke-*``).
        LOCAL_RUNTIME_CONFIG: Runtime-config handler ingress lane
            (IAM glob ``local.runtime_config.*``).
    """

    PATTERN_B_BROKER = "pattern-b-broker"
    PHASE5_MSK_SMOKE = "phase5-msk-smoke"
    LOCAL_RUNTIME_CONFIG = "local.runtime_config"

    def separator(self) -> str:
        """Return the separator the IAM glob requires between prefix and scope.

        Returns:
            ``"."`` for dotted prefixes, ``"-"`` for hyphenated prefixes.

        Example:
            >>> EnumReservedGroupPrefix.PATTERN_B_BROKER.separator()
            '-'
            >>> EnumReservedGroupPrefix.LOCAL_RUNTIME_CONFIG.separator()
            '.'
        """
        return "." if self is EnumReservedGroupPrefix.LOCAL_RUNTIME_CONFIG else "-"

    def authorized_glob(self) -> str:
        """Return the IAM glob this prefix must be matched by.

        Example:
            >>> EnumReservedGroupPrefix.PATTERN_B_BROKER.authorized_glob()
            'pattern-b-broker-*'
        """
        return f"{self.value}{self.separator()}*"


__all__ = ["EnumReservedGroupPrefix"]
