# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Provenance of a measured or estimated call cost."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapCostMeasurementSource(UtilStrValueHelper, str, Enum):
    """Provenance of a measured or estimated call cost."""

    PROVIDER_REPORTED_CHARGE = "provider_reported_charge"
    ESTIMATED_LIST_PRICE = "estimated_list_price"
    UNPRICED = "unpriced"


__all__ = ["EnumModelSwapCostMeasurementSource"]
