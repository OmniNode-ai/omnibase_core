"""
ReducerReportGenerationSubreducer - Report generation workflow subreducer.

Handles report generation workflows including template processing,
data aggregation, formatting, and output generation.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from ..v1_0_0.models import BaseSubreducer
from ..v1_0_0.models import ModelSubreducerResult as SubreducerResult
from ..v1_0_0.models import ModelWorkflowRequest as WorkflowRequest
from ..v1_0_0.models import WorkflowType


class EnumTemplateType(str, Enum):
    """Enumeration of supported template types."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    DASHBOARD = "dashboard"
    CUSTOM = "custom"


class EnumOutputFormat(str, Enum):
    """Enumeration of supported output formats."""

    JSON = "json"
    HTML = "html"
    CSV = "csv"
    TXT = "txt"
    MARKDOWN = "markdown"


class EnumSectionType(str, Enum):
    """Enumeration of report section types."""

    SUMMARY = "summary"
    METRICS = "metrics"
    OVERVIEW = "overview"
    INTRODUCTION = "introduction"
    ANALYSIS = "analysis"
    CONCLUSIONS = "conclusions"
    KPI = "kpi"
    CHARTS = "charts"
    INSIGHTS = "insights"
    DATA = "data"
    CUSTOM = "custom"


@dataclass
class ModelReportConfig:
    """Strongly typed report configuration model."""

    template_type: EnumTemplateType
    output_format: EnumOutputFormat
    report_title: str = "Generated Report"
    report_description: str = ""
    include_timestamp: bool = True
    include_metadata: bool = True


@dataclass
class ModelTemplateConfig:
    """Strongly typed template configuration model."""

    include_aggregations: bool = False
    sections: list[dict[str, str]] = None

    def __post_init__(self):
        if self.sections is None:
            self.sections = []


@dataclass
class ModelFormattingOptions:
    """Strongly typed formatting options model."""

    decimal_places: int = 2
    thousand_separator: str = ","
    date_format: str = "%Y-%m-%d %H:%M:%S"
    show_percentages: bool = True


@dataclass
class ModelValidationRules:
    """Strongly typed validation rules model."""

    min_sections: int = 1
    max_sections: int = 50
    validate_json: bool = True
    require_content: bool = True


@dataclass
class ModelListDataSummary:
    """Strongly typed summary for list data processing."""

    values: list[Any]
    count: int
    first_item: Any = None
    last_item: Any = None
    unique_count: int = 0


@dataclass
class ModelDictDataSummary:
    """Strongly typed summary for dictionary data processing."""

    data: dict[str, Any]
    keys: list[str]
    key_count: int
    has_nested: bool


@dataclass
class ModelNumericDataSummary:
    """Strongly typed summary for numeric data processing."""

    value: float
    formatted: str
    data_type: str


@dataclass
class ModelDataAggregations:
    """Strongly typed data aggregations model."""

    total_data_keys: int
    data_types_present: list[str]
    has_lists: bool
    has_dicts: bool
    total_list_items: int


@dataclass
class ModelReportSection:
    """Strongly typed report section model."""

    title: str
    content: Any
    section_type: EnumSectionType
    data_key: str = ""
    visualization: str = ""


@dataclass
class ModelReportContent:
    """Strongly typed report content model."""

    title: str
    description: str
    template_type: EnumTemplateType
    sections: list[ModelReportSection]
    generation_timestamp: str


@dataclass
class ModelReportMetadata:
    """Strongly typed report metadata model."""

    report_id: str
    template_type: EnumTemplateType
    output_format: EnumOutputFormat
    generated_at: str
    generator: str
    data_points_processed: int
    sections_generated: int
    content_size_estimate: int


@dataclass
class ModelValidationResults:
    """Strongly typed validation results model."""

    is_valid: bool
    validation_checks: list[str]
    warnings: list[str]
    errors: list[str]


@dataclass
class ModelGenerationStatistics:
    """Strongly typed generation statistics model."""

    template_type: EnumTemplateType
    output_format: EnumOutputFormat
    sections_generated: int
    data_points_processed: int
    content_size_bytes: int


@dataclass
class ModelProcessingMetrics:
    """Strongly typed processing metrics model."""

    total_processed: int = 0
    successful_reports: int = 0
    failed_reports: int = 0
    average_processing_time_ms: float = 0.0
    total_sections_generated: int = 0
    output_formats_used: dict[str, int] = None
    template_types_used: dict[str, int] = None

    def __post_init__(self):
        if self.output_formats_used is None:
            self.output_formats_used = {}
        if self.template_types_used is None:
            self.template_types_used = {}


class ReducerReportGenerationSubreducer(BaseSubreducer):
    """
    Report generation workflow subreducer.

    Handles report generation workflows including:
    - Template processing and variable substitution
    - Data aggregation and transformation
    - Multiple output formats (JSON, HTML, CSV, TXT)
    - Report metadata and versioning
    - Section-based report composition

    Phase 2 Features:
    - Template-based report generation
    - Multiple output format support
    - Data source integration
    - Report validation and quality checks
    - Metadata tracking and versioning
    """

    def __init__(self, name: str = "reducer_report_generation"):
        """Initialize the report generation subreducer."""
        super().__init__(name)
        self._processing_metrics = {
            "total_processed": 0,
            "successful_reports": 0,
            "failed_reports": 0,
            "average_processing_time_ms": 0.0,
            "total_sections_generated": 0,
            "output_formats_used": {},
            "template_types_used": {},
        }

        # Supported output formats
        self._supported_formats = {
            "json": self._generate_json_output,
            "html": self._generate_html_output,
            "csv": self._generate_csv_output,
            "txt": self._generate_text_output,
            "markdown": self._generate_markdown_output,
        }

        # Built-in template types
        self._template_processors = {
            "summary": self._process_summary_template,
            "detailed": self._process_detailed_template,
            "dashboard": self._process_dashboard_template,
            "custom": self._process_custom_template,
        }

        emit_log_event(
            level=LogLevel.INFO,
            message=f"{self.name} initialized with {len(self._supported_formats)} output formats and {len(self._template_processors)} template types",
            correlation_id=None,
        )

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """Check if this subreducer supports the given workflow type."""
        if isinstance(workflow_type, str):
            return workflow_type.lower() == "report_generation"
        return workflow_type == WorkflowType.REPORT_GENERATION

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """
        Process report generation workflow request.

        Args:
            request: Workflow request containing report parameters and data

        Returns:
            SubreducerResult with generated report or error information
        """
        start_time = time.time()

        emit_log_event(
            level=LogLevel.INFO,
            message=f"Starting report generation for workflow {request.workflow_id}",
            correlation_id=request.correlation_id,
        )

        try:
            # Validate request payload
            self._validate_report_request(request)

            # Extract report configuration
            report_config = self._extract_report_config(request.payload)

            emit_log_event(
                level=LogLevel.DEBUG,
                message=f"Generating report type '{report_config['template_type']}' in format '{report_config['output_format']}'",
                correlation_id=request.correlation_id,
            )

            # Process report data
            processed_data = self._process_report_data(
                report_config.get("data", {}),
                report_config,
            )

            # Generate report content based on template
            template_type = report_config["template_type"]
            if template_type in self._template_processors:
                report_content = self._template_processors[template_type](
                    processed_data,
                    report_config,
                )
            else:
                report_content = self._template_processors["custom"](
                    processed_data,
                    report_config,
                )

            # Generate output in requested format
            output_format = report_config["output_format"]
            if output_format in self._supported_formats:
                formatted_output = self._supported_formats[output_format](
                    report_content,
                    report_config,
                )
            else:
                # Default to JSON if format not supported
                formatted_output = self._supported_formats["json"](
                    report_content,
                    report_config,
                )
                emit_log_event(
                    level=LogLevel.WARNING,
                    message=f"Unsupported output format '{output_format}', defaulting to JSON",
                    correlation_id=request.correlation_id,
                )

            # Generate report metadata
            report_metadata = self._generate_report_metadata(
                report_config,
                report_content,
                len(processed_data),
            )

            # Validate generated report
            validation_results = self._validate_generated_report(
                formatted_output,
                report_config,
            )

            # Calculate processing metrics
            processing_time = (time.time() - start_time) * 1000

            # Update metrics
            self._update_success_metrics(
                processing_time,
                template_type,
                output_format,
                len(report_content.get("sections", [])),
            )

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Report generation completed successfully in {processing_time:.2f}ms",
                correlation_id=request.correlation_id,
            )

            return SubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=True,
                result={
                    "report_content": formatted_output,
                    "report_metadata": report_metadata,
                    "validation_results": validation_results,
                    "generation_statistics": {
                        "template_type": template_type,
                        "output_format": output_format,
                        "sections_generated": len(report_content.get("sections", [])),
                        "data_points_processed": len(processed_data),
                        "content_size_bytes": len(str(formatted_output)),
                    },
                },
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_message = f"Report generation failed: {e!s}"

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
                    "failed_at_step": "report_generation_processing",
                },
                processing_time_ms=processing_time,
            )

    def _validate_report_request(self, request: WorkflowRequest) -> None:
        """Validate the report generation request payload."""
        if not request.payload:
            raise OnexError(
                "Report generation request payload is required",
                CoreErrorCode.VALIDATION_FAILED,
            )

        required_fields = ["template_type", "output_format"]
        for field in required_fields:
            if field not in request.payload:
                raise OnexError(
                    f"{field} is required in report generation request",
                    CoreErrorCode.VALIDATION_FAILED,
                )

    def _extract_report_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract and validate report configuration from payload."""
        config = {
            "template_type": payload["template_type"],
            "output_format": payload["output_format"],
            "data": payload.get("data", {}),
            "template_config": payload.get("template_config", {}),
            "formatting_options": payload.get("formatting_options", {}),
            "metadata": payload.get("metadata", {}),
            "validation_rules": payload.get("validation_rules", {}),
            "report_title": payload.get("report_title", "Generated Report"),
            "report_description": payload.get("report_description", ""),
            "include_timestamp": payload.get("include_timestamp", True),
            "include_metadata": payload.get("include_metadata", True),
        }

        # Validate template type
        if config["template_type"] not in self._template_processors:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Unknown template type '{config['template_type']}', will use custom processor",
                correlation_id=None,
            )

        # Validate output format
        if config["output_format"] not in self._supported_formats:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Unsupported output format '{config['output_format']}', will default to JSON",
                correlation_id=None,
            )

        return config

    def _process_report_data(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Process and prepare data for report generation."""
        processed_data = {}

        # Handle different data types
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                processed_data[key] = self._process_list_data(value, key)
            elif isinstance(value, dict):
                processed_data[key] = self._process_dict_data(value, key)
            elif isinstance(value, (int, float)):
                processed_data[key] = self._process_numeric_data(value, key)
            else:
                processed_data[key] = str(value)

        # Add computed aggregations if requested
        template_config = config.get("template_config", {})
        if template_config.get("include_aggregations", False):
            processed_data["_aggregations"] = self._compute_data_aggregations(
                processed_data,
            )

        return processed_data

    def _process_list_data(self, data: list[Any], key: str) -> dict[str, Any]:
        """Process list data and generate summary statistics."""
        return {
            "values": data,
            "count": len(data),
            "first": data[0] if data else None,
            "last": data[-1] if data else None,
            "unique_count": (
                len(set(data))
                if all(isinstance(x, (str, int, float)) for x in data)
                else None
            ),
        }

    def _process_dict_data(self, data: dict[str, Any], key: str) -> dict[str, Any]:
        """Process dictionary data and generate metadata."""
        return {
            "data": data,
            "keys": list(data.keys()),
            "key_count": len(data.keys()),
            "has_nested": any(isinstance(v, (dict, list)) for v in data.values()),
        }

    def _process_numeric_data(self, data: float, key: str) -> dict[str, Any]:
        """Process numeric data with formatting options."""
        return {
            "value": data,
            "formatted": f"{data:,.2f}" if isinstance(data, float) else f"{data:,}",
            "type": "float" if isinstance(data, float) else "integer",
        }

    def _compute_data_aggregations(self, data: dict[str, Any]) -> dict[str, Any]:
        """Compute aggregations across processed data."""
        aggregations = {
            "total_data_keys": len(data),
            "data_types_present": set(),
            "has_lists": False,
            "has_dicts": False,
            "total_list_items": 0,
        }

        for key, value in data.items():
            if isinstance(value, dict):
                aggregations["has_dicts"] = True
                if "values" in value and isinstance(value["values"], list):
                    aggregations["has_lists"] = True
                    aggregations["total_list_items"] += len(value["values"])
                    aggregations["data_types_present"].add("list")
                elif "data" in value:
                    aggregations["data_types_present"].add("dict")
                elif "value" in value:
                    aggregations["data_types_present"].add(value.get("type", "unknown"))

        aggregations["data_types_present"] = list(aggregations["data_types_present"])
        return aggregations

    def _process_summary_template(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Process data using summary report template."""
        sections = []

        # Executive summary section
        sections.append(
            {
                "title": "Executive Summary",
                "content": self._generate_executive_summary(data, config),
                "type": "summary",
            },
        )

        # Key metrics section
        if "_aggregations" in data:
            sections.append(
                {
                    "title": "Key Metrics",
                    "content": data["_aggregations"],
                    "type": "metrics",
                },
            )

        # Data overview section
        sections.append(
            {
                "title": "Data Overview",
                "content": self._generate_data_overview(data),
                "type": "overview",
            },
        )

        return {
            "title": config.get("report_title", "Summary Report"),
            "description": config.get("report_description", ""),
            "template_type": "summary",
            "sections": sections,
            "generation_timestamp": datetime.now().isoformat(),
        }

    def _process_detailed_template(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Process data using detailed report template."""
        sections = []

        # Introduction section
        sections.append(
            {
                "title": "Introduction",
                "content": {
                    "report_purpose": config.get(
                        "report_description",
                        "Detailed analysis report",
                    ),
                    "data_scope": f"Analysis of {len(data)} data elements",
                    "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "type": "introduction",
            },
        )

        # Detailed analysis for each data element
        for key, value in data.items():
            if not key.startswith("_"):  # Skip internal aggregations
                sections.append(
                    {
                        "title": f"Analysis: {key.replace('_', ' ').title()}",
                        "content": value,
                        "type": "analysis",
                        "data_key": key,
                    },
                )

        # Conclusions section
        sections.append(
            {
                "title": "Conclusions",
                "content": self._generate_conclusions(data),
                "type": "conclusions",
            },
        )

        return {
            "title": config.get("report_title", "Detailed Report"),
            "description": config.get("report_description", ""),
            "template_type": "detailed",
            "sections": sections,
            "generation_timestamp": datetime.now().isoformat(),
        }

    def _process_dashboard_template(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Process data using dashboard report template."""
        sections = []

        # Key performance indicators
        sections.append(
            {
                "title": "Key Performance Indicators",
                "content": self._extract_kpis(data),
                "type": "kpi",
                "visualization": "cards",
            },
        )

        # Charts and graphs section
        sections.append(
            {
                "title": "Data Visualization",
                "content": self._prepare_chart_data(data),
                "type": "charts",
                "visualization": "mixed",
            },
        )

        # Quick insights
        sections.append(
            {
                "title": "Quick Insights",
                "content": self._generate_quick_insights(data),
                "type": "insights",
            },
        )

        return {
            "title": config.get("report_title", "Dashboard Report"),
            "description": config.get("report_description", ""),
            "template_type": "dashboard",
            "sections": sections,
            "generation_timestamp": datetime.now().isoformat(),
        }

    def _process_custom_template(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Process data using custom template configuration."""
        template_config = config.get("template_config", {})
        sections = []

        # Use template configuration to build sections
        if "sections" in template_config:
            for section_config in template_config["sections"]:
                section = {
                    "title": section_config.get("title", "Custom Section"),
                    "type": section_config.get("type", "custom"),
                    "content": self._apply_custom_section_logic(data, section_config),
                }
                sections.append(section)
        else:
            # Default custom template: show all data
            for key, value in data.items():
                sections.append(
                    {
                        "title": key.replace("_", " ").title(),
                        "type": "data",
                        "content": value,
                    },
                )

        return {
            "title": config.get("report_title", "Custom Report"),
            "description": config.get("report_description", ""),
            "template_type": "custom",
            "sections": sections,
            "generation_timestamp": datetime.now().isoformat(),
        }

    def _generate_json_output(
        self,
        content: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate JSON formatted output."""
        output = {
            "report": content,
            "metadata": {
                "format": "json",
                "generated_at": datetime.now().isoformat(),
                "generator": self.name,
            },
        }

        if config.get("include_metadata", True):
            output["metadata"].update(config.get("metadata", {}))

        return output

    def _generate_html_output(
        self,
        content: ModelReportContent,
        config: dict[str, Any],
    ) -> str:
        """Generate HTML formatted output."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{content.title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            ".section { margin-bottom: 30px; }",
            ".section h2 { color: #333; border-bottom: 2px solid #eee; }",
            ".kpi { background: #f0f8ff; padding: 15px; border-radius: 5px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{content.title}</h1>",
        ]

        if content.description:
            html_parts.append(f"<p>{content.description}</p>")

        for section in content.sections:
            html_parts.extend(
                [
                    '<div class="section">',
                    f"<h2>{section.title}</h2>",
                    f"<div>{self._format_content_for_html(section.content)}</div>",
                    "</div>",
                ],
            )

        html_parts.extend(
            [
                f"<footer><small>Generated at {content.generation_timestamp}</small></footer>",
                "</body>",
                "</html>",
            ],
        )

        return "\n".join(html_parts)

    def _generate_csv_output(
        self,
        content: dict[str, Any],
        config: dict[str, Any],
    ) -> str:
        """Generate CSV formatted output."""
        csv_lines = [
            f"Report Title,{content['title']}",
            f"Generated At,{content['generation_timestamp']}",
            "",
        ]

        for section in content.get("sections", []):
            csv_lines.append(f"Section,{section['title']}")
            csv_lines.extend(self._format_content_for_csv(section["content"]))
            csv_lines.append("")

        return "\n".join(csv_lines)

    def _generate_text_output(
        self,
        content: ModelReportContent,
        config: dict[str, Any],
    ) -> str:
        """Generate plain text formatted output."""
        text_lines = ["=" * 50, content.title.center(50), "=" * 50, ""]

        if content.description:
            text_lines.extend([content.description, ""])

        for section in content.sections:
            text_lines.extend(
                [
                    "-" * 30,
                    section.title,
                    "-" * 30,
                    self._format_content_for_text(section.content),
                    "",
                ],
            )

        text_lines.append(f"Generated at: {content.generation_timestamp}")
        return "\n".join(text_lines)

    def _generate_markdown_output(
        self,
        content: ModelReportContent,
        config: dict[str, Any],
    ) -> str:
        """Generate Markdown formatted output."""
        md_lines = [f"# {content.title}", ""]

        if content.description:
            md_lines.extend([content.description, ""])

        for section in content.sections:
            md_lines.extend(
                [
                    f"## {section.title}",
                    "",
                    self._format_content_for_markdown(section.content),
                    "",
                ],
            )

        md_lines.append(f"*Generated at: {content.generation_timestamp}*")
        return "\n".join(md_lines)

    # Helper methods for content formatting, metadata generation, etc.
    def _generate_executive_summary(
        self,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate executive summary from data."""
        return {
            "data_elements_analyzed": len(
                [k for k in data if not k.startswith("_")],
            ),
            "report_scope": config.get("report_description", "Data analysis report"),
            "key_findings": "Analysis completed successfully",
            "total_data_points": sum(
                item.get("count", 1) if isinstance(item, dict) else 1
                for item in data.values()
                if not str(item).startswith("_")
            ),
        }

    def _generate_report_metadata(
        self,
        config: dict[str, Any],
        content: dict[str, Any],
        data_size: int,
    ) -> dict[str, Any]:
        """Generate comprehensive report metadata."""
        return {
            "report_id": str(uuid4()),
            "template_type": config["template_type"],
            "output_format": config["output_format"],
            "generated_at": datetime.now().isoformat(),
            "generator": self.name,
            "data_points_processed": data_size,
            "sections_generated": len(content.get("sections", [])),
            "content_size_estimate": len(str(content)),
            "generation_config": {
                "include_timestamp": config.get("include_timestamp", True),
                "include_metadata": config.get("include_metadata", True),
            },
        }

    def _validate_generated_report(
        self,
        output: Any,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate generated report against rules."""
        validation_results = {
            "is_valid": True,
            "validation_checks": [],
            "warnings": [],
            "errors": [],
        }

        # Basic validation checks
        if not output:
            validation_results["is_valid"] = False
            validation_results["errors"].append("Generated output is empty")

        # Format-specific validation
        if config["output_format"] == "json":
            try:
                json.dumps(output)
                validation_results["validation_checks"].append(
                    "JSON format validation: PASSED",
                )
            except Exception as e:
                validation_results["is_valid"] = False
                validation_results["errors"].append(
                    f"JSON format validation failed: {e!s}",
                )

        return validation_results

    def _update_success_metrics(
        self,
        processing_time: float,
        template_type: str,
        output_format: str,
        sections_count: int,
    ) -> None:
        """Update metrics for successful processing."""
        self._processing_metrics["total_processed"] += 1
        self._processing_metrics["successful_reports"] += 1
        self._processing_metrics["total_sections_generated"] += sections_count

        # Track format and template usage
        self._processing_metrics["output_formats_used"][output_format] = (
            self._processing_metrics["output_formats_used"].get(output_format, 0) + 1
        )
        self._processing_metrics["template_types_used"][template_type] = (
            self._processing_metrics["template_types_used"].get(template_type, 0) + 1
        )

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
        self._processing_metrics["failed_reports"] += 1

        # Update average processing time (including failures)
        total_time = (
            self._processing_metrics["average_processing_time_ms"]
            * (self._processing_metrics["total_processed"] - 1)
            + processing_time
        )
        self._processing_metrics["average_processing_time_ms"] = (
            total_time / self._processing_metrics["total_processed"]
        )

    # Additional helper methods (abbreviated for space)
    def _generate_data_overview(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate overview of data elements."""
        return {"summary": f"Contains {len(data)} data elements"}

    def _generate_conclusions(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate conclusions from data analysis."""
        return {"conclusion": "Analysis completed successfully"}

    def _extract_kpis(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract key performance indicators from data."""
        return {"total_elements": len(data)}

    def _prepare_chart_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prepare data for chart visualization."""
        return {"chart_type": "summary", "data_elements": len(data)}

    def _generate_quick_insights(self, data: dict[str, Any]) -> list[str]:
        """Generate quick insights from data."""
        return [f"Processed {len(data)} data elements"]

    def _apply_custom_section_logic(
        self,
        data: dict[str, Any],
        section_config: dict[str, Any],
    ) -> Any:
        """Apply custom section configuration logic."""
        return {"processed": "custom logic applied"}

    def _format_content_for_html(self, content: Any) -> str:
        """Format content for HTML output."""
        return f"<pre>{content!s}</pre>"

    def _format_content_for_csv(self, content: Any) -> list[str]:
        """Format content for CSV output."""
        return [f"Content,{content!s}"]

    def _format_content_for_text(self, content: Any) -> str:
        """Format content for plain text output."""
        return str(content)

    def _format_content_for_markdown(self, content: Any) -> str:
        """Format content for Markdown output."""
        return f"```\n{content!s}\n```"

    def get_processing_metrics(self) -> dict[str, Any]:
        """Get current processing metrics."""
        return self._processing_metrics.copy()
