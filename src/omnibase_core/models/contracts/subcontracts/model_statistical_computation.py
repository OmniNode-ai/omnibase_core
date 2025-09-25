#!/usr/bin/env python3
"""
Statistical Computation Model - ONEX Standards Compliant.

Individual model for statistical computation configuration.
Part of the Aggregation Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelStatisticalComputation(BaseModel):
    """
    Statistical computation configuration.

    Defines statistical functions, approximations,
    and advanced analytical computations.
    """

    statistical_enabled: bool = Field(
        default=False,
        description="Enable statistical computations",
    )

    statistical_functions: list[str] = Field(
        default_factory=list,
        description="Statistical functions to compute",
    )

    percentiles: list[float] = Field(
        default_factory=list,
        description="Percentiles to calculate",
    )

    approximation_enabled: bool = Field(
        default=False,
        description="Enable approximation algorithms",
    )

    approximation_error_tolerance: float = Field(
        default=0.01,
        description="Error tolerance for approximations",
        ge=0.001,
        le=0.1,
    )

    histogram_enabled: bool = Field(
        default=False,
        description="Enable histogram computation",
    )

    histogram_buckets: int = Field(
        default=10,
        description="Number of histogram buckets",
        ge=2,
    )

    outlier_detection: bool = Field(
        default=False,
        description="Enable outlier detection",
    )

    outlier_threshold: float = Field(
        default=2.0,
        description="Threshold for outlier detection",
        ge=0.5,
    )
