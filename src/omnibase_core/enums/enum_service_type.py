# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Service type enum.

The EnumServiceType enum for defining
infrastructure service types in the ONEX Configuration-Driven Registry System.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumServiceType(UtilStrValueHelper, str, Enum):
    """Standard service type categories."""

    KAFKA = "kafka"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"
    MONGODB = "mongodb"
    REST_API = "rest_api"
    GRPC = "grpc"
    RABBITMQ = "rabbitmq"
    VAULT = "vault"
    S3 = "s3"
    CUSTOM = "custom"


__all__ = ["EnumServiceType"]
