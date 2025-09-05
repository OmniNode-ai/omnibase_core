"""
ReducerDataAnalysisSubreducer - Data analysis workflow subreducer.

Handles statistical data analysis workflows including data validation,
transformation, statistical processing, and result aggregation.
"""

import statistics
import time
from typing import Any, Dict, List, Optional, Union

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from ..v1_0_0.models import (
    BaseSubreducer,
)
from ..v1_0_0.models import ModelSubreducerResult as SubreducerResult
from ..v1_0_0.models import ModelWorkflowRequest as WorkflowRequest
from ..v1_0_0.models import (
    WorkflowType,
)


class ReducerDataAnalysisSubreducer(BaseSubreducer):
    """
    Data analysis workflow subreducer.

    Handles data analysis workflows including:
    - Data validation and cleansing
    - Statistical analysis (mean, median, mode, std dev)
    - Data transformation and aggregation
    - Trend analysis and correlation detection
    - Results formatting and export

    Phase 2 Features:
    - Multiple analysis types (descriptive, correlation, trend)
    - Configurable data validation rules
    - Statistical processing with error handling
    - Comprehensive analysis reporting
    - Performance optimization for large datasets
    """

    def __init__(self, name: str = "reducer_data_analysis"):
        """Initialize the data analysis subreducer."""
        super().__init__(name)
        self._processing_metrics = {
            "total_processed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time_ms": 0.0,
            "total_data_points_analyzed": 0,
            "analysis_types_used": {},
        }

        # Supported analysis types
        self._supported_analyses = {
            "descriptive": self._perform_descriptive_analysis,
            "correlation": self._perform_correlation_analysis,
            "trend": self._perform_trend_analysis,
            "distribution": self._perform_distribution_analysis,
        }

        emit_log_event(
            level=LogLevel.INFO,
            message=f"{self.name} initialized with {len(self._supported_analyses)} analysis types",
            correlation_id=None,
        )

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """Check if this subreducer supports the given workflow type."""
        if isinstance(workflow_type, str):
            return workflow_type.lower() == "data_analysis"
        return workflow_type == WorkflowType.DATA_ANALYSIS

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """
        Process data analysis workflow request.

        Args:
            request: Workflow request containing analysis parameters and data

        Returns:
            SubreducerResult with analysis results or error information
        """
        start_time = time.time()

        emit_log_event(
            level=LogLevel.INFO,
            message=f"Starting data analysis for workflow {request.workflow_id}",
            correlation_id=request.correlation_id,
        )

        try:
            # Validate request payload
            self._validate_analysis_request(request)

            # Extract analysis parameters
            analysis_config = self._extract_analysis_config(request.payload)
            data = analysis_config.get("data", [])
            analysis_types = analysis_config.get("analysis_types", ["descriptive"])

            emit_log_event(
                level=LogLevel.DEBUG,
                message=f"Processing {len(data)} data points with analysis types: {analysis_types}",
                correlation_id=request.correlation_id,
            )

            # Perform data validation and cleansing
            cleaned_data = self._validate_and_clean_data(data, analysis_config)

            # Execute requested analyses
            analysis_results = {}
            for analysis_type in analysis_types:
                if analysis_type in self._supported_analyses:
                    emit_log_event(
                        level=LogLevel.DEBUG,
                        message=f"Executing {analysis_type} analysis",
                        correlation_id=request.correlation_id,
                    )

                    analysis_func = self._supported_analyses[analysis_type]
                    analysis_results[analysis_type] = analysis_func(
                        cleaned_data, analysis_config
                    )

                    # Track analysis type usage
                    self._processing_metrics["analysis_types_used"][analysis_type] = (
                        self._processing_metrics["analysis_types_used"].get(
                            analysis_type, 0
                        )
                        + 1
                    )
                else:
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Unsupported analysis type: {analysis_type}",
                        correlation_id=request.correlation_id,
                    )

            # Generate comprehensive analysis summary
            analysis_summary = self._generate_analysis_summary(
                analysis_results, cleaned_data, analysis_config
            )

            # Calculate processing metrics
            processing_time = (time.time() - start_time) * 1000

            # Update metrics
            self._update_success_metrics(processing_time, len(cleaned_data))

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Data analysis completed successfully in {processing_time:.2f}ms",
                correlation_id=request.correlation_id,
            )

            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=True,
                result={
                    "analysis_results": analysis_results,
                    "analysis_summary": analysis_summary,
                    "data_statistics": {
                        "original_data_points": len(data),
                        "cleaned_data_points": len(cleaned_data),
                        "analysis_types_performed": analysis_types,
                        "data_quality_score": self._calculate_data_quality_score(
                            data, cleaned_data
                        ),
                    },
                },
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_message = f"Data analysis failed: {str(e)}"

            self._update_failure_metrics(processing_time, str(type(e).__name__))

            emit_log_event(
                level=LogLevel.ERROR,
                message=error_message,
                correlation_id=request.correlation_id,
            )

            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=False,
                error_message=error_message,
                error_details={
                    "error_type": type(e).__name__,
                    "error_description": str(e),
                    "failed_at_step": "data_analysis_processing",
                },
                processing_time_ms=processing_time,
            )

    def _validate_analysis_request(self, request: WorkflowRequest) -> None:
        """Validate the analysis request payload."""
        if not request.payload:
            raise OnexError(
                "Analysis request payload is required", CoreErrorCode.VALIDATION_FAILED
            )

        if "data" not in request.payload:
            raise OnexError(
                "Data field is required in analysis request",
                CoreErrorCode.VALIDATION_FAILED,
            )

        data = request.payload["data"]
        if not isinstance(data, list) or len(data) == 0:
            raise OnexError(
                "Data must be a non-empty list", CoreErrorCode.VALIDATION_FAILED
            )

    def _extract_analysis_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate analysis configuration from payload."""
        config = {
            "data": payload["data"],
            "analysis_types": payload.get("analysis_types", ["descriptive"]),
            "data_validation": payload.get(
                "data_validation", {"remove_outliers": True, "handle_missing": True}
            ),
            "statistical_config": payload.get(
                "statistical_config", {"confidence_level": 0.95}
            ),
            "output_format": payload.get("output_format", "detailed"),
        }

        # Validate analysis types
        invalid_types = [
            t for t in config["analysis_types"] if t not in self._supported_analyses
        ]
        if invalid_types:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Invalid analysis types will be skipped: {invalid_types}",
                correlation_id=None,
            )
            config["analysis_types"] = [
                t for t in config["analysis_types"] if t in self._supported_analyses
            ]

        if not config["analysis_types"]:
            config["analysis_types"] = ["descriptive"]  # Default fallback

        return config

    def _validate_and_clean_data(
        self, data: List[Any], config: Dict[str, Any]
    ) -> List[float]:
        """Validate and clean input data for analysis."""
        cleaned_data = []
        validation_config = config.get("data_validation", {})

        # Convert to numeric values and handle missing data
        for item in data:
            try:
                if item is None and validation_config.get("handle_missing", True):
                    continue  # Skip missing values

                numeric_value = float(item)
                if not (numeric_value != numeric_value):  # Check for NaN
                    cleaned_data.append(numeric_value)

            except (ValueError, TypeError):
                if not validation_config.get("handle_missing", True):
                    raise OnexError(
                        f"Invalid numeric value: {item}",
                        CoreErrorCode.VALIDATION_FAILED,
                    )
                # Skip non-numeric values if configured to handle missing data

        if len(cleaned_data) == 0:
            raise OnexError(
                "No valid numeric data points found", CoreErrorCode.VALIDATION_FAILED
            )

        # Remove outliers if configured
        if validation_config.get("remove_outliers", False):
            cleaned_data = self._remove_outliers(cleaned_data)

        return cleaned_data

    def _remove_outliers(self, data: List[float]) -> List[float]:
        """Remove statistical outliers using IQR method."""
        if len(data) < 4:
            return data  # Need at least 4 points for meaningful outlier detection

        sorted_data = sorted(data)
        q1_idx = len(sorted_data) // 4
        q3_idx = 3 * len(sorted_data) // 4

        q1 = sorted_data[q1_idx]
        q3 = sorted_data[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        return [x for x in data if lower_bound <= x <= upper_bound]

    def _perform_descriptive_analysis(
        self, data: List[float], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform descriptive statistical analysis."""
        if len(data) == 0:
            return {"error": "No data available for descriptive analysis"}

        try:
            return {
                "count": len(data),
                "mean": statistics.mean(data),
                "median": statistics.median(data),
                "mode": statistics.mode(data) if len(set(data)) < len(data) else None,
                "std_dev": statistics.stdev(data) if len(data) > 1 else 0.0,
                "variance": statistics.variance(data) if len(data) > 1 else 0.0,
                "min": min(data),
                "max": max(data),
                "range": max(data) - min(data),
                "quartiles": {
                    "q1": (
                        statistics.quantiles(data, n=4)[0] if len(data) >= 4 else None
                    ),
                    "q2": statistics.median(data),
                    "q3": (
                        statistics.quantiles(data, n=4)[2] if len(data) >= 4 else None
                    ),
                },
            }
        except statistics.StatisticsError as e:
            return {"error": f"Statistical analysis error: {str(e)}"}

    def _perform_correlation_analysis(
        self, data: List[float], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform correlation analysis (simplified version for single dataset)."""
        if len(data) < 2:
            return {"error": "Insufficient data for correlation analysis"}

        # For single dataset, analyze autocorrelation with lag-1
        if len(data) < 3:
            return {
                "autocorrelation_lag1": 0.0,
                "note": "Insufficient data for meaningful correlation",
            }

        # Calculate lag-1 autocorrelation
        data_current = data[1:]
        data_lagged = data[:-1]

        try:
            correlation = statistics.correlation(data_current, data_lagged)
            return {
                "autocorrelation_lag1": correlation,
                "data_points_used": len(data_current),
                "interpretation": self._interpret_correlation(correlation),
            }
        except statistics.StatisticsError:
            return {"error": "Could not calculate correlation - insufficient variance"}

    def _perform_trend_analysis(
        self, data: List[float], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform trend analysis using simple linear regression."""
        if len(data) < 3:
            return {"error": "Insufficient data for trend analysis"}

        try:
            # Simple linear regression: y = mx + b
            n = len(data)
            x_values = list(range(n))

            # Calculate slope (trend)
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(data)

            numerator = sum(
                (x_values[i] - x_mean) * (data[i] - y_mean) for i in range(n)
            )
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator

            intercept = y_mean - slope * x_mean

            # Calculate R-squared
            y_pred = [slope * x + intercept for x in x_values]
            ss_res = sum((data[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((data[i] - y_mean) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return {
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_squared,
                "trend_direction": (
                    "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
                ),
                "trend_strength": self._classify_trend_strength(
                    abs(slope), max(data) - min(data)
                ),
                "data_points": n,
            }

        except Exception as e:
            return {"error": f"Trend analysis failed: {str(e)}"}

    def _perform_distribution_analysis(
        self, data: List[float], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze data distribution characteristics."""
        if len(data) < 2:
            return {"error": "Insufficient data for distribution analysis"}

        try:
            mean = statistics.mean(data)
            std_dev = statistics.stdev(data) if len(data) > 1 else 0.0

            # Calculate skewness (simplified)
            if std_dev == 0:
                skewness = 0.0
            else:
                skewness = sum(((x - mean) / std_dev) ** 3 for x in data) / len(data)

            # Calculate kurtosis (simplified)
            if std_dev == 0:
                kurtosis = 0.0
            else:
                kurtosis = (
                    sum(((x - mean) / std_dev) ** 4 for x in data) / len(data) - 3
                )

            return {
                "distribution_type": self._classify_distribution(skewness, kurtosis),
                "skewness": skewness,
                "kurtosis": kurtosis,
                "normality_indicators": {
                    "skewness_normal": abs(skewness) < 2.0,
                    "kurtosis_normal": abs(kurtosis) < 7.0,
                },
            }

        except Exception as e:
            return {"error": f"Distribution analysis failed: {str(e)}"}

    def _generate_analysis_summary(
        self, results: Dict[str, Any], data: List[float], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis summary."""
        summary = {
            "total_data_points": len(data),
            "analyses_performed": list(results.keys()),
            "data_quality": "good" if len(data) > 10 else "limited",
            "key_insights": [],
        }

        # Extract key insights from results
        if "descriptive" in results:
            desc = results["descriptive"]
            if "mean" in desc and "std_dev" in desc:
                cv = (
                    desc["std_dev"] / desc["mean"]
                    if desc["mean"] != 0
                    else float("inf")
                )
                summary["key_insights"].append(
                    f"Coefficient of variation: {cv:.3f} ({'high' if cv > 0.5 else 'moderate' if cv > 0.2 else 'low'} variability)"
                )

        if "trend" in results:
            trend = results["trend"]
            if "trend_direction" in trend and "r_squared" in trend:
                summary["key_insights"].append(
                    f"Trend: {trend['trend_direction']} with R² = {trend['r_squared']:.3f}"
                )

        return summary

    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation coefficient."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            strength = "strong"
        elif abs_corr >= 0.5:
            strength = "moderate"
        elif abs_corr >= 0.3:
            strength = "weak"
        else:
            strength = "very weak"

        direction = "positive" if correlation > 0 else "negative"
        return f"{strength} {direction} correlation"

    def _classify_trend_strength(self, slope: float, data_range: float) -> str:
        """Classify trend strength based on slope and data range."""
        if data_range == 0:
            return "no trend"

        normalized_slope = abs(slope) / data_range
        if normalized_slope > 0.1:
            return "strong"
        elif normalized_slope > 0.05:
            return "moderate"
        elif normalized_slope > 0.01:
            return "weak"
        else:
            return "very weak"

    def _classify_distribution(self, skewness: float, kurtosis: float) -> str:
        """Classify distribution type based on skewness and kurtosis."""
        if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
            return "approximately normal"
        elif skewness > 1:
            return "right-skewed"
        elif skewness < -1:
            return "left-skewed"
        elif kurtosis > 3:
            return "heavy-tailed"
        elif kurtosis < -1:
            return "light-tailed"
        else:
            return "moderately non-normal"

    def _calculate_data_quality_score(
        self, original_data: List[Any], cleaned_data: List[float]
    ) -> float:
        """Calculate data quality score based on cleaning results."""
        if len(original_data) == 0:
            return 0.0

        retention_rate = len(cleaned_data) / len(original_data)

        # Additional quality factors
        uniqueness = (
            len(set(cleaned_data)) / len(cleaned_data) if len(cleaned_data) > 0 else 0
        )
        completeness = retention_rate

        # Weighted quality score
        quality_score = 0.6 * completeness + 0.4 * uniqueness
        return min(1.0, max(0.0, quality_score))

    def _update_success_metrics(self, processing_time: float, data_points: int) -> None:
        """Update metrics for successful processing."""
        self._processing_metrics["total_processed"] += 1
        self._processing_metrics["successful_analyses"] += 1
        self._processing_metrics["total_data_points_analyzed"] += data_points

        # Update average processing time
        total_time = (
            self._processing_metrics["average_processing_time_ms"]
            * (self._processing_metrics["total_processed"] - 1)
            + processing_time
        )
        self._processing_metrics["average_processing_time_ms"] = (
            total_time / self._processing_metrics["total_processed"]
        )

    def _update_failure_metrics(self, processing_time: float, error_type: str) -> None:
        """Update metrics for failed processing."""
        self._processing_metrics["total_processed"] += 1
        self._processing_metrics["failed_analyses"] += 1

        # Update average processing time (including failures)
        total_time = (
            self._processing_metrics["average_processing_time_ms"]
            * (self._processing_metrics["total_processed"] - 1)
            + processing_time
        )
        self._processing_metrics["average_processing_time_ms"] = (
            total_time / self._processing_metrics["total_processed"]
        )

    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics."""
        return self._processing_metrics.copy()
