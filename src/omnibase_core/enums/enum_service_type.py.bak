from __future__ import annotations

"""
Service type enum.

This module provides the EnumServiceType enum for defining
infrastructure service types in the ONEX Configuration-Driven Registry System.
"""

from enum import Enum, unique


@unique
class EnumServiceType(str, Enum):
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
    CONSUL = "consul"
    VAULT = "vault"
    S3 = "s3"
    CUSTOM = "custom"


__all__ = ["EnumServiceType"]
