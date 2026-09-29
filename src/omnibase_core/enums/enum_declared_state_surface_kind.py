# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Observable surfaces of deployment-declared state."""

from enum import StrEnum, unique


@unique
class EnumDeclaredStateSurfaceKind(StrEnum):
    """The kind of surface a declared-state observation reads."""

    BROKER_ACL = "broker_acl"
    COMPOSE_SERVICE = "compose_service"
    HOST_SETTING = "host_setting"
    DEPLOYED_BUNDLE = "deployed_bundle"


__all__ = ["EnumDeclaredStateSurfaceKind"]
