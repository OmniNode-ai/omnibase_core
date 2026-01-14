"""
Instance type enumeration for cloud and service instances.

Provides strongly typed instance type values for connection configurations.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumInstanceType(StrValueHelper, str, Enum):
    """
    Strongly typed instance type for cloud and service configurations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    # AWS EC2 Instance Types
    T2_NANO = "t2.nano"
    T2_MICRO = "t2.micro"
    T2_SMALL = "t2.small"
    T2_MEDIUM = "t2.medium"
    T2_LARGE = "t2.large"
    T3_MICRO = "t3.micro"
    T3_SMALL = "t3.small"
    T3_MEDIUM = "t3.medium"
    T3_LARGE = "t3.large"
    T3_XLARGE = "t3.xlarge"

    # General Purpose
    M5_LARGE = "m5.large"
    M5_XLARGE = "m5.xlarge"
    M5_2XLARGE = "m5.2xlarge"
    M5_4XLARGE = "m5.4xlarge"

    # Compute Optimized
    C5_LARGE = "c5.large"
    C5_XLARGE = "c5.xlarge"
    C5_2XLARGE = "c5.2xlarge"
    C5_4XLARGE = "c5.4xlarge"

    # Memory Optimized
    R5_LARGE = "r5.large"
    R5_XLARGE = "r5.xlarge"
    R5_2XLARGE = "r5.2xlarge"
    R5_4XLARGE = "r5.4xlarge"

    # Storage Optimized
    I3_LARGE = "i3.large"
    I3_XLARGE = "i3.xlarge"
    I3_2XLARGE = "i3.2xlarge"

    # Azure VM Sizes
    AZURE_B1S = "B1s"
    AZURE_B1MS = "B1ms"
    AZURE_B2S = "B2s"
    AZURE_B2MS = "B2ms"
    AZURE_D2S_V3 = "D2s_v3"
    AZURE_D4S_V3 = "D4s_v3"
    AZURE_D8S_V3 = "D8s_v3"

    # Google Cloud Machine Types
    GCP_F1_MICRO = "f1-micro"
    GCP_G1_SMALL = "g1-small"
    GCP_N1_STANDARD_1 = "n1-standard-1"
    GCP_N1_STANDARD_2 = "n1-standard-2"
    GCP_N1_STANDARD_4 = "n1-standard-4"
    GCP_N1_STANDARD_8 = "n1-standard-8"

    # Container/Docker
    CONTAINER_SMALL = "container.small"
    CONTAINER_MEDIUM = "container.medium"
    CONTAINER_LARGE = "container.large"
    CONTAINER_XLARGE = "container.xlarge"

    # Database Instances
    DB_T2_MICRO = "db.t2.micro"
    DB_T2_SMALL = "db.t2.small"
    DB_T2_MEDIUM = "db.t2.medium"
    DB_T3_MICRO = "db.t3.micro"
    DB_T3_SMALL = "db.t3.small"
    DB_T3_MEDIUM = "db.t3.medium"

    # Custom/Generic
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"
    XXLARGE = "xxlarge"

    @classmethod
    def is_aws_instance(cls, instance_type: EnumInstanceType) -> bool:
        """Check if the instance type is an AWS instance."""
        aws_prefixes = ("t2.", "t3.", "m5.", "c5.", "r5.", "i3.")
        return instance_type.value.startswith(aws_prefixes)

    @classmethod
    def is_azure_instance(cls, instance_type: EnumInstanceType) -> bool:
        """Check if the instance type is an Azure instance."""
        azure_instances = {
            cls.AZURE_B1S,
            cls.AZURE_B1MS,
            cls.AZURE_B2S,
            cls.AZURE_B2MS,
            cls.AZURE_D2S_V3,
            cls.AZURE_D4S_V3,
            cls.AZURE_D8S_V3,
        }
        return instance_type in azure_instances

    @classmethod
    def is_gcp_instance(cls, instance_type: EnumInstanceType) -> bool:
        """Check if the instance type is a Google Cloud instance."""
        gcp_prefixes = ("f1-", "g1-", "n1-")
        return instance_type.value.startswith(gcp_prefixes)

    @classmethod
    def is_database_instance(cls, instance_type: EnumInstanceType) -> bool:
        """Check if the instance type is for databases."""
        return instance_type.value.startswith("db.")

    @classmethod
    def is_container_instance(cls, instance_type: EnumInstanceType) -> bool:
        """Check if the instance type is for containers."""
        return instance_type.value.startswith("container.")

    @classmethod
    def get_size_category(cls, instance_type: EnumInstanceType) -> str:
        """Get the general size category for the instance."""
        micro_instances = {
            cls.T2_NANO,
            cls.T2_MICRO,
            cls.T3_MICRO,
            cls.GCP_F1_MICRO,
            cls.DB_T2_MICRO,
            cls.DB_T3_MICRO,
        }
        small_instances = {
            cls.T2_SMALL,
            cls.T3_SMALL,
            cls.GCP_G1_SMALL,
            cls.DB_T2_SMALL,
            cls.DB_T3_SMALL,
            cls.CONTAINER_SMALL,
            cls.SMALL,
        }
        medium_instances = {
            cls.T2_MEDIUM,
            cls.T3_MEDIUM,
            cls.M5_LARGE,
            cls.C5_LARGE,
            cls.R5_LARGE,
            cls.DB_T2_MEDIUM,
            cls.DB_T3_MEDIUM,
            cls.CONTAINER_MEDIUM,
            cls.MEDIUM,
        }

        if instance_type in micro_instances:
            return "micro"
        if instance_type in small_instances:
            return "small"
        if instance_type in medium_instances:
            return "medium"
        if "xlarge" in instance_type.value.lower():
            return "xlarge"
        return "large"


# Export for use
__all__ = ["EnumInstanceType"]
