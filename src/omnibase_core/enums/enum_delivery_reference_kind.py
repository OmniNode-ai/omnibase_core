# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery reference kind values."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDeliveryReferenceKind"]


@unique
class EnumDeliveryReferenceKind(UtilStrValueHelper, str, Enum):
    """Declared delivery reference kind."""

    DEV_MERGE_TAG = "dev_merge_tag"
    CANDIDATE_TAG = "candidate_tag"
    GATE_BOOTSTRAP_PIN = "gate_bootstrap_pin"
    DECLARED_DEPENDENCY_PIN = "declared_dependency_pin"
    BRANCH = "branch"
    SHA = "sha"
    HAND_KEPT_VERSION = "hand_kept_version"
    BUMP_PR = "bump_pr"
    UNKNOWN = "unknown"
