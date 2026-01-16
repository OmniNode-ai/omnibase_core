"""Decision report generator service for corpus replay evidence (OMN-1199).

Generates decision-ready reports from corpus replay evidence in multiple formats:
- CLI: Formatted terminal output with configurable verbosity
- JSON: Structured data for machine consumption
- Markdown: GitHub-flavored markdown for PRs and documentation
- HTML: Standalone HTML with inline CSS for dashboards

Thread Safety:
    ServiceDecisionReportGenerator is stateless and thread-safe. All methods
    take inputs and return outputs without modifying any shared state.

Output Determinism:
    Report methods that include timestamps (generate_json_report, generate_markdown_report,
    generate_html_report) accept an optional `generated_at` parameter. When provided,
    output is fully deterministic and reproducible. When omitted, current UTC time is used,
    making output time-dependent.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.rendering.renderer_report_cli import RendererReportCli
from omnibase_core.rendering.renderer_report_html import RendererReportHtml
from omnibase_core.rendering.renderer_report_json import RendererReportJson
from omnibase_core.rendering.renderer_report_markdown import RendererReportMarkdown
from omnibase_core.types.typed_dict_decision_report import TypedDictDecisionReport

# Cost data unavailability warning message (used in recommendation generation)
COST_NA_WARNING = "Cost data incomplete - manual cost review recommended"


class ServiceDecisionReportGenerator:
    """Generate decision-ready reports from corpus replay evidence.

    This service transforms ModelEvidenceSummary and ModelExecutionComparison data
    into human-readable and machine-readable report formats suitable for different
    stakeholders and use cases.

    Runtime Configuration:
        All recommendation thresholds can be customized at instantiation time.
        If not provided, class-level constants are used as defaults.

    Thread Safety:
        This service is stateless per-call and thread-safe. Instance attributes
        are set once during initialization and never modified. All methods take
        inputs and return outputs without modifying any shared state. Multiple
        threads can safely call any method concurrently.

    Output Determinism:
        Report methods that include timestamps (generate_json_report,
        generate_markdown_report, generate_html_report) accept an optional
        `generated_at` parameter. When provided, output is fully deterministic
        and reproducible for testing. When omitted, current UTC time is used,
        making output time-dependent.

    Example:
        >>> from omnibase_core.services.service_decision_report_generator import (
        ...     ServiceDecisionReportGenerator
        ... )
        >>> # Use default thresholds
        >>> generator = ServiceDecisionReportGenerator()
        >>> cli_report = generator.generate_cli_report(summary, comparisons)
        >>> print(cli_report)
        >>>
        >>> # Custom thresholds for stricter review
        >>> strict_generator = ServiceDecisionReportGenerator(
        ...     confidence_approve_threshold=0.95,
        ...     pass_rate_minimum=0.85,
        ... )

    .. versionadded:: 0.6.5
    """

    # Recommendation thresholds - confidence levels
    CONFIDENCE_APPROVE_THRESHOLD: float = 0.9
    CONFIDENCE_REVIEW_THRESHOLD: float = 0.7

    # Recommendation thresholds - pass rate
    PASS_RATE_OPTIMAL: float = 0.95
    PASS_RATE_MINIMUM: float = 0.70

    # Recommendation thresholds - latency regression (percent)
    LATENCY_BLOCKER_PERCENT: float = 50.0
    LATENCY_WARNING_PERCENT: float = 20.0

    # Recommendation thresholds - cost regression (percent)
    COST_BLOCKER_PERCENT: float = 50.0
    COST_WARNING_PERCENT: float = 20.0

    @staticmethod
    def _init_threshold(value: float | None, default: float) -> float:
        """Initialize a threshold value with a default fallback.

        This helper reduces boilerplate in __init__ by providing a consistent
        pattern for initializing optional threshold parameters.

        Args:
            value: The user-provided value, or None to use the default.
            default: The default value to use when value is None.

        Returns:
            The provided value if not None, otherwise the default.
        """
        return value if value is not None else default

    def __init__(
        self,
        confidence_approve_threshold: float | None = None,
        confidence_review_threshold: float | None = None,
        pass_rate_optimal: float | None = None,
        pass_rate_minimum: float | None = None,
        latency_blocker_percent: float | None = None,
        latency_warning_percent: float | None = None,
        cost_blocker_percent: float | None = None,
        cost_warning_percent: float | None = None,
    ) -> None:
        """Initialize report generator with optional threshold overrides.

        Args:
            confidence_approve_threshold: Minimum confidence for auto-approve.
                Defaults to CONFIDENCE_APPROVE_THRESHOLD (0.9).
            confidence_review_threshold: Minimum confidence for review recommendation.
                Defaults to CONFIDENCE_REVIEW_THRESHOLD (0.7).
            pass_rate_optimal: Target pass rate (below triggers warning).
                Defaults to PASS_RATE_OPTIMAL (0.95).
            pass_rate_minimum: Minimum pass rate (below triggers blocker).
                Defaults to PASS_RATE_MINIMUM (0.70).
            latency_blocker_percent: Latency increase percentage that triggers blocker.
                Defaults to LATENCY_BLOCKER_PERCENT (50.0).
            latency_warning_percent: Latency increase percentage that triggers warning.
                Defaults to LATENCY_WARNING_PERCENT (20.0).
            cost_blocker_percent: Cost increase percentage that triggers blocker.
                Defaults to COST_BLOCKER_PERCENT (50.0).
            cost_warning_percent: Cost increase percentage that triggers warning.
                Defaults to COST_WARNING_PERCENT (20.0).

        Raises:
            ModelOnexError: If any threshold value is out of valid range or if
                threshold relationships are violated.

        Validation Rules:
            Range Validation:
                - confidence_approve_threshold: Must be in [0.0, 1.0]
                - confidence_review_threshold: Must be in [0.0, 1.0]
                - pass_rate_optimal: Must be in [0.0, 1.0]
                - pass_rate_minimum: Must be in [0.0, 1.0]
                - latency_blocker_percent: Must be >= 0
                - latency_warning_percent: Must be >= 0
                - cost_blocker_percent: Must be >= 0
                - cost_warning_percent: Must be >= 0

            Relationship Validation:
                - confidence_approve_threshold >= confidence_review_threshold
                  (approve requires higher confidence than review)
                - pass_rate_optimal >= pass_rate_minimum
                  (optimal target must be at least the minimum)
                - latency_blocker_percent >= latency_warning_percent
                  (blockers triggered at higher regression than warnings)
                - cost_blocker_percent >= cost_warning_percent
                  (blockers triggered at higher regression than warnings)
        """
        # Initialize thresholds with defaults using helper
        self.confidence_approve_threshold = self._init_threshold(
            confidence_approve_threshold, self.CONFIDENCE_APPROVE_THRESHOLD
        )
        self.confidence_review_threshold = self._init_threshold(
            confidence_review_threshold, self.CONFIDENCE_REVIEW_THRESHOLD
        )
        self.pass_rate_optimal = self._init_threshold(
            pass_rate_optimal, self.PASS_RATE_OPTIMAL
        )
        self.pass_rate_minimum = self._init_threshold(
            pass_rate_minimum, self.PASS_RATE_MINIMUM
        )
        self.latency_blocker_percent = self._init_threshold(
            latency_blocker_percent, self.LATENCY_BLOCKER_PERCENT
        )
        self.latency_warning_percent = self._init_threshold(
            latency_warning_percent, self.LATENCY_WARNING_PERCENT
        )
        self.cost_blocker_percent = self._init_threshold(
            cost_blocker_percent, self.COST_BLOCKER_PERCENT
        )
        self.cost_warning_percent = self._init_threshold(
            cost_warning_percent, self.COST_WARNING_PERCENT
        )

        # Validate threshold ranges
        if not (0.0 <= self.confidence_approve_threshold <= 1.0):
            raise ModelOnexError(
                message=f"confidence_approve_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_approve_threshold}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.confidence_approve_threshold},
            )
        if not (0.0 <= self.confidence_review_threshold <= 1.0):
            raise ModelOnexError(
                message=f"confidence_review_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_review_threshold}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.confidence_review_threshold},
            )
        if not (0.0 <= self.pass_rate_optimal <= 1.0):
            raise ModelOnexError(
                message=f"pass_rate_optimal must be between 0.0 and 1.0, "
                f"got {self.pass_rate_optimal}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.pass_rate_optimal},
            )
        if not (0.0 <= self.pass_rate_minimum <= 1.0):
            raise ModelOnexError(
                message=f"pass_rate_minimum must be between 0.0 and 1.0, "
                f"got {self.pass_rate_minimum}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.pass_rate_minimum},
            )
        if self.latency_blocker_percent < 0:
            raise ModelOnexError(
                message=f"latency_blocker_percent must be >= 0, "
                f"got {self.latency_blocker_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.latency_blocker_percent},
            )
        if self.latency_warning_percent < 0:
            raise ModelOnexError(
                message=f"latency_warning_percent must be >= 0, "
                f"got {self.latency_warning_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.latency_warning_percent},
            )
        if self.cost_blocker_percent < 0:
            raise ModelOnexError(
                message=f"cost_blocker_percent must be >= 0, "
                f"got {self.cost_blocker_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.cost_blocker_percent},
            )
        if self.cost_warning_percent < 0:
            raise ModelOnexError(
                message=f"cost_warning_percent must be >= 0, "
                f"got {self.cost_warning_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"threshold": self.cost_warning_percent},
            )

        # Validate threshold relationships
        if self.confidence_approve_threshold < self.confidence_review_threshold:
            raise ModelOnexError(
                message=f"confidence_approve_threshold ({self.confidence_approve_threshold}) "
                f"must be >= confidence_review_threshold ({self.confidence_review_threshold})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "approve": self.confidence_approve_threshold,
                    "review": self.confidence_review_threshold,
                },
            )
        if self.pass_rate_optimal < self.pass_rate_minimum:
            raise ModelOnexError(
                message=f"pass_rate_optimal ({self.pass_rate_optimal}) "
                f"must be >= pass_rate_minimum ({self.pass_rate_minimum})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "optimal": self.pass_rate_optimal,
                    "minimum": self.pass_rate_minimum,
                },
            )
        if self.latency_blocker_percent < self.latency_warning_percent:
            raise ModelOnexError(
                message=f"latency_blocker_percent ({self.latency_blocker_percent}) "
                f"must be >= latency_warning_percent ({self.latency_warning_percent})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "blocker": self.latency_blocker_percent,
                    "warning": self.latency_warning_percent,
                },
            )
        if self.cost_blocker_percent < self.cost_warning_percent:
            raise ModelOnexError(
                message=f"cost_blocker_percent ({self.cost_blocker_percent}) "
                f"must be >= cost_warning_percent ({self.cost_warning_percent})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "blocker": self.cost_blocker_percent,
                    "warning": self.cost_warning_percent,
                },
            )

    def _ensure_recommendation(
        self,
        summary: ModelEvidenceSummary,
        recommendation: ModelDecisionRecommendation | None,
    ) -> ModelDecisionRecommendation:
        """Ensure a recommendation exists, generating one if needed.

        Args:
            summary: Evidence summary used to generate recommendation if needed.
            recommendation: Pre-generated recommendation, or None to generate.

        Returns:
            The provided recommendation or a newly generated one.
        """
        if recommendation is None:
            return self.generate_recommendation(summary)
        return recommendation

    def generate_cli_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        verbosity: Literal["minimal", "standard", "verbose"] = "standard",
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> str:
        """Generate formatted CLI output for terminal display.

        Creates a fixed-width (80 character) formatted report suitable for
        terminal output with configurable verbosity levels.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons (used in verbose mode).
            verbosity: Output detail level:
                - "minimal": Headline and recommendation only
                - "standard": Full summary with sections
                - "verbose": Everything including comparison details
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.

        Returns:
            Formatted string report for terminal display.

        Example:
            >>> report = generator.generate_cli_report(summary, [], "standard")
            >>> print(report)

        Raises:
            ModelOnexError: If comparisons is not a list.
        """
        if not isinstance(comparisons, list):
            raise ModelOnexError(
                message="comparisons must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"comparisons_type": type(comparisons).__name__},
            )

        recommendation = self._ensure_recommendation(summary, recommendation)
        return RendererReportCli.render(summary, comparisons, recommendation, verbosity)

    def generate_json_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        include_details: bool = False,
        recommendation: ModelDecisionRecommendation | None = None,
        generated_at: datetime | None = None,
    ) -> TypedDictDecisionReport:
        """Generate structured JSON report for machine consumption.

        Creates a JSON-serializable dictionary with all evidence data suitable
        for API responses, storage, or further processing. Output is deterministic
        when a fixed `generated_at` timestamp is provided.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            include_details: Whether to include individual comparison details.
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.

        Returns:
            TypedDictDecisionReport with report data.

        Example:
            >>> report = generator.generate_json_report(summary, comparisons)
            >>> json_str = json.dumps(report, sort_keys=True)

        Raises:
            ModelOnexError: If comparisons is not a list.
        """
        if not isinstance(comparisons, list):
            raise ModelOnexError(
                message="comparisons must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"comparisons_type": type(comparisons).__name__},
            )

        recommendation = self._ensure_recommendation(summary, recommendation)
        return RendererReportJson.render(
            summary, comparisons, recommendation, include_details, generated_at
        )

    def generate_markdown_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        include_details: bool = True,
        recommendation: ModelDecisionRecommendation | None = None,
        generated_at: datetime | None = None,
    ) -> str:
        """Generate Markdown report for PR/documentation.

        Creates GitHub-flavored markdown suitable for pull request descriptions,
        documentation, or other markdown-rendering contexts.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            include_details: Whether to include individual comparison details.
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.

        Returns:
            GitHub-flavored markdown string.

        Example:
            >>> md_report = generator.generate_markdown_report(summary, comparisons)
            >>> with open("report.md", "w") as f:
            ...     f.write(md_report)

        Raises:
            ModelOnexError: If comparisons is not a list.
        """
        if not isinstance(comparisons, list):
            raise ModelOnexError(
                message="comparisons must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"comparisons_type": type(comparisons).__name__},
            )

        recommendation = self._ensure_recommendation(summary, recommendation)
        return RendererReportMarkdown.render(
            summary,
            comparisons,
            recommendation,
            include_details,
            generated_at,
            self.latency_warning_percent,
            self.cost_warning_percent,
        )

    def generate_html_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        include_details: bool = True,
        recommendation: ModelDecisionRecommendation | None = None,
        generated_at: datetime | None = None,
        standalone: bool = True,
    ) -> str:
        """Generate HTML report for web display.

        Creates standalone HTML with inline CSS suitable for dashboards
        and web views.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            include_details: Whether to include individual comparison details.
            recommendation: Pre-generated recommendation. If None, generates a new one.
            generated_at: Optional timestamp for report generation.
            standalone: If True, generate full HTML document. If False, just content div.

        Returns:
            HTML string with inline CSS.

        Raises:
            ModelOnexError: If comparisons is not a list.
        """
        if not isinstance(comparisons, list):
            raise ModelOnexError(
                message="comparisons must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"comparisons_type": type(comparisons).__name__},
            )

        recommendation = self._ensure_recommendation(summary, recommendation)
        return RendererReportHtml.render(
            summary,
            comparisons,
            recommendation,
            include_details,
            generated_at,
            standalone,
        )

    def generate_recommendation(
        self,
        summary: ModelEvidenceSummary,
    ) -> ModelDecisionRecommendation:
        """Generate actionable recommendation from evidence.

        Analyzes the evidence summary and generates a recommendation with
        blockers, warnings, and next steps based on configurable instance
        thresholds. Thresholds can be customized at instantiation or use
        class constant defaults:

        - confidence_approve_threshold: Minimum confidence for auto-approve
        - confidence_review_threshold: Minimum confidence for review recommendation
        - pass_rate_optimal: Target pass rate (below triggers warning)
        - pass_rate_minimum: Minimum pass rate (below triggers blocker)
        - latency_blocker_percent: Latency increase that triggers blocker
        - latency_warning_percent: Latency increase that triggers warning
        - cost_blocker_percent: Cost increase that triggers blocker
        - cost_warning_percent: Cost increase that triggers warning

        Recommendation Logic:
            - **approve**: confidence >= confidence_approve_threshold AND
              no critical violations AND no blockers
            - **review**: confidence >= confidence_review_threshold AND
              no critical violations (warnings OK)
            - **reject**: confidence < confidence_review_threshold OR
              critical violations present

        Args:
            summary: Aggregated evidence summary from corpus replay.

        Returns:
            ModelDecisionRecommendation with action, confidence, blockers,
            warnings, and next steps.

        Example:
            >>> recommendation = generator.generate_recommendation(summary)
            >>> if recommendation.action == "approve":
            ...     print("Safe to merge!")
        """
        blockers: list[str] = []
        warnings: list[str] = []
        next_steps: list[str] = []

        confidence = summary.confidence_score
        violations = summary.invariant_violations

        # Check for critical violations (blockers)
        if violations.new_critical_violations > 0:
            blockers.append(
                f"{violations.new_critical_violations} new critical "
                f"invariant violation(s) detected"
            )

        # Check pass rate
        if summary.pass_rate < self.pass_rate_optimal:
            if summary.pass_rate < self.pass_rate_minimum:
                blockers.append(
                    f"Pass rate too low: {summary.pass_rate:.0%} "
                    f"(minimum: {self.pass_rate_minimum:.0%})"
                )
            else:
                warnings.append(
                    f"Pass rate below optimal: {summary.pass_rate:.0%} "
                    f"(target: {self.pass_rate_optimal:.0%})"
                )

        # Check latency regression
        latency_delta = summary.latency_stats.delta_avg_percent
        if latency_delta > self.latency_blocker_percent:
            blockers.append(
                f"Significant latency regression: +{latency_delta:.0f}% "
                f"(threshold: {self.latency_blocker_percent:.0f}%)"
            )
        elif latency_delta > self.latency_warning_percent:
            warnings.append(
                f"Latency increased: +{latency_delta:.0f}% (consider optimization)"
            )

        # Check cost regression
        if summary.cost_stats is not None:
            cost_delta = summary.cost_stats.delta_percent
            if cost_delta > self.cost_blocker_percent:
                blockers.append(
                    f"Significant cost increase: +{cost_delta:.0f}% "
                    f"(threshold: {self.cost_blocker_percent:.0f}%)"
                )
            elif cost_delta > self.cost_warning_percent:
                warnings.append(
                    f"Cost increased: +{cost_delta:.0f}% (consider optimization)"
                )
        else:
            # Warn about incomplete cost data
            warnings.append(COST_NA_WARNING)

        # Check for new violations (non-critical)
        if violations.new_violations > 0 and violations.new_critical_violations == 0:
            warnings.append(
                f"{violations.new_violations} new non-critical violation(s) detected"
            )

        # Determine action based on logic
        has_critical = violations.new_critical_violations > 0
        has_blockers = len(blockers) > 0

        if (
            confidence >= self.confidence_approve_threshold
            and not has_critical
            and not has_blockers
        ):
            action: Literal["approve", "review", "reject"] = "approve"
            rationale = "High confidence score with no critical violations or blockers."
        elif confidence >= self.confidence_review_threshold and not has_critical:
            action = "review"
            rationale = (
                "Acceptable confidence but requires human review due to warnings."
            )
        else:
            action = "reject"
            if has_critical:
                rationale = "Critical violations detected that must be resolved."
            elif confidence < self.confidence_review_threshold:
                rationale = f"Confidence too low ({confidence:.0%}) for approval."
            else:
                rationale = "Blocking issues detected that must be resolved."

        # Generate next steps based on action
        if action == "approve":
            next_steps = [
                "Review the summary to confirm expected behavior",
                "Proceed with merge/deployment",
            ]
        elif action == "review":
            next_steps = [
                "Review warnings and assess risk",
                "Run additional targeted tests if needed",
                "Consider performance optimization if latency/cost increased",
                "Approve or request changes based on review",
            ]
        else:  # reject
            if has_critical:
                next_steps.append("Fix critical invariant violations")
            if summary.pass_rate < self.pass_rate_minimum:
                next_steps.append("Investigate and fix failing test cases")
            if latency_delta > self.latency_blocker_percent:
                next_steps.append("Optimize code to reduce latency regression")
            if (
                summary.cost_stats
                and summary.cost_stats.delta_percent > self.cost_blocker_percent
            ):
                next_steps.append("Optimize to reduce cost increase")
            next_steps.append("Re-run corpus replay after fixes")

        return ModelDecisionRecommendation(
            action=action,
            confidence=confidence,
            blockers=blockers,
            warnings=warnings,
            next_steps=next_steps,
            rationale=rationale,
        )

    def _validate_file_path(self, path: Path) -> None:
        """Validate file path to prevent path traversal attacks.

        Checks that the path does not contain traversal patterns like ".."
        that could allow writing to arbitrary locations.

        Args:
            path: The path to validate.

        Raises:
            ModelOnexError: If path contains traversal patterns or is invalid.
        """
        # FIX (PR #368): Check for ".." as actual path *components* rather than
        # substring matching. This prevents false positives for legitimate
        # filenames containing ".." (e.g., "file..backup.md"). Only reject
        # paths where ".." is a directory component used for traversal.
        path_str = str(path)
        if ".." in path.parts:
            raise ModelOnexError(
                message=f"Path traversal not allowed: {path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"path": path_str, "reason": "path_traversal_detected"},
            )

        # Resolve the path and validate it's well-formed
        try:
            path.resolve(strict=False)
        except (OSError, ValueError) as e:
            raise ModelOnexError(
                message=f"Invalid path: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"path": path_str, "error": str(e)},
            ) from e

    def save_to_file(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        path: Path,
        output_format: Literal["cli", "markdown", "json", "html"] = "markdown",
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> None:
        """Save report to file in specified format.

        Generates the report in the requested format and writes it to the specified
        file path. This is a convenience method that combines report generation
        and file writing.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            path: Path to save the file to.
            output_format: Output format - "cli", "markdown", "json", or "html".
            recommendation: Pre-generated recommendation. If None, generates a new one.

        Raises:
            ModelOnexError: If format is invalid, path contains traversal attempts,
                or file cannot be written.

        Example:
            >>> generator = ServiceDecisionReportGenerator()
            >>> generator.save_to_file(summary, comparisons, Path("report.md"))
        """
        # Validate path - prevent path traversal attacks
        self._validate_file_path(path)

        generators = {
            "cli": lambda: self.generate_cli_report(
                summary,
                comparisons,
                verbosity="standard",
                recommendation=recommendation,
            ),
            "markdown": lambda: self.generate_markdown_report(
                summary, comparisons, recommendation=recommendation
            ),
            "json": lambda: RendererReportJson.serialize(
                self.generate_json_report(
                    summary, comparisons, recommendation=recommendation
                )
            ),
            "html": lambda: self.generate_html_report(
                summary, comparisons, recommendation=recommendation
            ),
        }

        if output_format not in generators:
            raise ModelOnexError(
                message=f"Invalid format '{output_format}'. Must be one of: {list(generators.keys())}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "format": output_format,
                    "valid_formats": list(generators.keys()),
                },
            )

        content = generators[output_format]()
        try:
            path.write_text(content, encoding="utf-8")
        except PermissionError as e:
            raise ModelOnexError(
                message=f"Permission denied writing to {path}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                context={
                    "path": str(path),
                    "error": str(e),
                    "error_type": "permission_denied",
                },
            ) from e
        except FileNotFoundError as e:
            raise ModelOnexError(
                message=f"Parent directory does not exist for {path}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                context={
                    "path": str(path),
                    "error": str(e),
                    "error_type": "directory_not_found",
                },
            ) from e
        except OSError as e:
            # fallback-ok: generic I/O error handler for disk full, etc.
            raise ModelOnexError(
                message=f"Failed to write report to {path}: {e}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                context={"path": str(path), "format": output_format, "error": str(e)},
            ) from e

    def save_to_markdown(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        path: Path,
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> None:
        """Convenience method to save markdown report to file.

        This is a shorthand for calling save_to_file with format="markdown".

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            path: Path to save the markdown file to.
            recommendation: Pre-generated recommendation. If None, generates a new one.

        Example:
            >>> generator = ServiceDecisionReportGenerator()
            >>> generator.save_to_markdown(summary, comparisons, Path("report.md"))
        """
        self.save_to_file(
            summary,
            comparisons,
            path,
            output_format="markdown",
            recommendation=recommendation,
        )

    def generate_all_formats(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> dict[str, str]:
        """Generate report in all available formats.

        Convenience method that generates CLI, Markdown, JSON, and HTML
        formats in a single call. Generates the recommendation once
        and reuses it across all formats for consistency.

        Args:
            summary: The evidence summary to format.
            comparisons: Individual execution comparisons.
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation.

        Returns:
            Dictionary with format names as keys and formatted output as values:
            {
                "cli": "...",
                "markdown": "...",
                "json": "...",
                "html": "..."
            }

        Example:
            >>> generator = ServiceDecisionReportGenerator()
            >>> result = generator.generate_all_formats(summary, comparisons)
            >>> print(result["cli"])
            >>> with open("report.md", "w") as f:
            ...     f.write(result["markdown"])
        """
        # Generate recommendation once and reuse across all formats
        recommendation = self._ensure_recommendation(summary, recommendation)

        return {
            "cli": self.generate_cli_report(
                summary, comparisons, recommendation=recommendation
            ),
            "markdown": self.generate_markdown_report(
                summary, comparisons, recommendation=recommendation
            ),
            "json": RendererReportJson.serialize(
                self.generate_json_report(
                    summary, comparisons, recommendation=recommendation
                )
            ),
            "html": self.generate_html_report(
                summary, comparisons, recommendation=recommendation
            ),
        }


__all__ = [
    "COST_NA_WARNING",
    "ServiceDecisionReportGenerator",
]
