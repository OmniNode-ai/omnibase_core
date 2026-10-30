# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""State of one contract name in the node catalog (OMN-21589)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCatalogEntryState(UtilStrValueHelper, str, Enum):
    """State of one contract name in the catalog.

    A name the catalog has never been told about has no entry at all, so there is
    no member for it: absence is the lack of an entry, not a state an entry holds.

    Attributes:
        ANNOUNCED: A hash is held and pinned, admission has not run.
        ADMITTED: Admission passed; the lane lets this name start.
        REFUSED: Admission failed with a typed reason.
        WITHDRAWN: The package is gone; the name is not startable.
    """

    ANNOUNCED = "announced"
    ADMITTED = "admitted"
    REFUSED = "refused"
    WITHDRAWN = "withdrawn"
