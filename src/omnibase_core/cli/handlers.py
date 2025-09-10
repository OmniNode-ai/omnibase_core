"""
CLI command handlers for production ONEX operations.

Provides specialized handlers for different CLI commands including type quality analysis,
processing operations, status monitoring, and configuration management.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from omnibase_core.core.core_structured_logging import emit_log_event_sync
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .config import CLIConfig


class BaseHandler:
    """Base handler with common functionality for all CLI handlers."""

    def __init__(self, config: CLIConfig):
        self.config = config
        self.console = Console(force_terminal=config.output.colored)

    def _output_result(self, data: Any, success: bool = True) -> None:
        """Output result in the configured format."""
        if self.config.output.format == "json":
            output = {
                "success": success,
                "data": data,
                "timestamp": self._get_timestamp(),
            }
            click.echo(json.dumps(output, indent=2, default=str))
        elif self.config.output.format == "yaml":
            from omnibase_core.utils.safe_yaml_loader import serialize_data_to_yaml

            output = {
                "success": success,
                "data": data,
                "timestamp": self._get_timestamp(),
            }
            try:
                yaml_output = serialize_data_to_yaml(output, default_flow_style=False)
                click.echo(yaml_output)
            except Exception as e:
                # Fallback to JSON if YAML serialization fails
                click.echo(json.dumps(output, indent=2, default=str))
        else:
            # Text format
            if success:
                self.console.print(f"✅ {data}", style="green")
            else:
                self.console.print(f"❌ {data}", style="red")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow().isoformat()

    def _log_operation(self, operation: str, **kwargs) -> None:
        """Log operation with structured logging."""
        emit_log_event_sync(LogLevel.INFO, f"CLI operation: {operation}", kwargs)


class TypeQualityHandler(BaseHandler):
    """Handler for type quality analysis operations."""

    async def analyze_path(
        self,
        path: Path,
        output: Optional[Path] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Analyze type quality for code at the given path.

        Args:
            path: Path to analyze (file or directory)
            output: Optional output file path
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
        """
        self._log_operation(
            "type_quality_analysis",
            path=str(path),
            output=str(output) if output else None,
        )

        if not path.exists():
            self._output_result(f"Path does not exist: {path}", success=False)
            sys.exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=not self.config.output.progress_bars,
        ) as progress:

            task = progress.add_task("Analyzing type quality...", total=None)

            try:
                # Collect files to analyze
                files_to_analyze = self._collect_files(
                    path, include_patterns, exclude_patterns
                )
                progress.update(
                    task, description=f"Found {len(files_to_analyze)} files to analyze"
                )

                # Perform analysis
                results = await self._perform_type_analysis(
                    files_to_analyze, progress, task
                )

                # Generate report
                report = self._generate_type_quality_report(results)

                # Output results
                if output:
                    self._save_report(report, output)
                    self._output_result(f"Type quality report saved to {output}")
                else:
                    self._output_result(report)

            except Exception as e:
                self._output_result(f"Type quality analysis failed: {e}", success=False)
                sys.exit(1)

    def _collect_files(
        self,
        path: Path,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> List[Path]:
        """Collect Python files for analysis."""
        import fnmatch

        if path.is_file():
            return [path] if path.suffix == ".py" else []

        files = []
        include_patterns = include_patterns or ["*.py"]
        exclude_patterns = exclude_patterns or ["*/__pycache__/*", "*/.*", "*/tests/*"]

        for file_path in path.rglob("*.py"):
            # Check include patterns
            if not any(
                fnmatch.fnmatch(str(file_path), pattern) for pattern in include_patterns
            ):
                continue

            # Check exclude patterns
            if any(
                fnmatch.fnmatch(str(file_path), pattern) for pattern in exclude_patterns
            ):
                continue

            files.append(file_path)

        return files

    async def _perform_type_analysis(
        self, files: List[Path], progress: Progress, task_id: Any
    ) -> Dict[str, Any]:
        """Perform actual type analysis on collected files."""
        import subprocess

        results = {
            "files_analyzed": len(files),
            "total_issues": 0,
            "files_with_issues": 0,
            "issue_types": {},
            "file_results": [],
        }

        for i, file_path in enumerate(files):
            progress.update(
                task_id, description=f"Analyzing {file_path.name} ({i+1}/{len(files)})"
            )

            try:
                # Run mypy on the file
                result = subprocess.run(
                    ["python", "-m", "mypy", str(file_path), "--show-error-codes"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                file_result = self._parse_mypy_output(
                    file_path, result.stdout, result.stderr
                )
                results["file_results"].append(file_result)

                if file_result["issues"]:
                    results["files_with_issues"] += 1
                    results["total_issues"] += len(file_result["issues"])

                    # Count issue types
                    for issue in file_result["issues"]:
                        issue_type = issue.get("error_code", "unknown")
                        results["issue_types"][issue_type] = (
                            results["issue_types"].get(issue_type, 0) + 1
                        )

            except subprocess.TimeoutExpired:
                file_result = {
                    "file": str(file_path),
                    "status": "timeout",
                    "issues": [],
                    "analysis_time": 30.0,
                }
                results["file_results"].append(file_result)
            except Exception as e:
                file_result = {
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e),
                    "issues": [],
                    "analysis_time": 0.0,
                }
                results["file_results"].append(file_result)

        return results

    def _parse_mypy_output(
        self, file_path: Path, stdout: str, stderr: str
    ) -> Dict[str, Any]:
        """Parse mypy output into structured format."""
        import re
        import time

        start_time = time.time()

        issues = []

        # Parse mypy output lines
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            # Match mypy error format: file.py:line:column: error: message [error-code]
            match = re.match(
                r"^(.+):(\d+):(\d+):\s+(error|warning|note):\s+(.+?)(?:\s+\[(.+)\])?$",
                line,
            )
            if match:
                _, line_num, col_num, severity, message, error_code = match.groups()
                issues.append(
                    {
                        "line": int(line_num),
                        "column": int(col_num),
                        "severity": severity,
                        "message": message,
                        "error_code": error_code or "unknown",
                    }
                )

        return {
            "file": str(file_path),
            "status": "success",
            "issues": issues,
            "analysis_time": time.time() - start_time,
        }

    def _generate_type_quality_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive type quality report."""
        # Calculate quality score
        total_files = results["files_analyzed"]
        files_with_issues = results["files_with_issues"]
        total_issues = results["total_issues"]

        if total_files == 0:
            quality_score = 100.0
        else:
            # Score based on files without issues and average issues per file
            clean_files_ratio = (total_files - files_with_issues) / total_files
            avg_issues_per_file = total_issues / total_files

            # Quality score: 70% clean files + 30% issue density
            quality_score = (clean_files_ratio * 70) + max(
                0, (1 - avg_issues_per_file / 10) * 30
            )
            quality_score = min(100.0, max(0.0, quality_score))

        report = {
            "summary": {
                "files_analyzed": total_files,
                "files_with_issues": files_with_issues,
                "total_issues": total_issues,
                "quality_score": round(quality_score, 2),
                "grade": self._calculate_grade(quality_score),
            },
            "issue_breakdown": results["issue_types"],
            "top_issues": self._get_top_issues(results["issue_types"]),
            "recommendations": self._generate_recommendations(results),
            "details": results["file_results"],
        }

        return report

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from quality score."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        else:
            return "F"

    def _get_top_issues(self, issue_types: Dict[str, int]) -> List[Dict[str, Any]]:
        """Get top 5 most common issues."""
        sorted_issues = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)
        return [
            {"error_code": code, "count": count} for code, count in sorted_issues[:5]
        ]

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        issue_types = results["issue_types"]
        total_issues = results["total_issues"]

        if total_issues == 0:
            recommendations.append("Excellent! No type issues found.")
            return recommendations

        # Specific recommendations based on common issues
        if issue_types.get("import-untyped", 0) > 0:
            recommendations.append(
                "Consider adding type stubs or using typed alternatives for untyped imports"
            )

        if issue_types.get("no-untyped-def", 0) > 0:
            recommendations.append("Add type annotations to function definitions")

        if issue_types.get("var-annotated", 0) > 0:
            recommendations.append("Add type annotations to variable declarations")

        if issue_types.get("return-value", 0) > 0:
            recommendations.append(
                "Ensure functions return values matching their type annotations"
            )

        if total_issues > 50:
            recommendations.append(
                "Consider running mypy with --strict mode for comprehensive type checking"
            )

        return recommendations

    def _save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == ".json":
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
        elif output_path.suffix in [".yaml", ".yml"]:
            from omnibase_core.utils.safe_yaml_loader import serialize_data_to_yaml

            try:
                yaml_output = serialize_data_to_yaml(report, default_flow_style=False)
                with open(output_path, "w") as f:
                    f.write(yaml_output)
            except Exception as e:
                # Fallback to JSON if YAML serialization fails
                with open(output_path.with_suffix(".json"), "w") as f:
                    json.dump(report, f, indent=2, default=str)
        else:
            # Text format
            with open(output_path, "w") as f:
                f.write(self._format_report_text(report))

    def _format_report_text(self, report: Dict[str, Any]) -> str:
        """Format report as human-readable text."""
        lines = []

        lines.append("ONEX Type Quality Report")
        lines.append("=" * 50)
        lines.append("")

        summary = report["summary"]
        lines.append(f"Files Analyzed: {summary['files_analyzed']}")
        lines.append(f"Files with Issues: {summary['files_with_issues']}")
        lines.append(f"Total Issues: {summary['total_issues']}")
        lines.append(f"Quality Score: {summary['quality_score']}% ({summary['grade']})")
        lines.append("")

        if report["top_issues"]:
            lines.append("Top Issues:")
            for issue in report["top_issues"]:
                lines.append(f"  - {issue['error_code']}: {issue['count']} occurrences")
            lines.append("")

        if report["recommendations"]:
            lines.append("Recommendations:")
            for rec in report["recommendations"]:
                lines.append(f"  • {rec}")
            lines.append("")

        return "\n".join(lines)


class ProcessHandler(BaseHandler):
    """Handler for processing operations with Smart Responder Chain."""

    async def process_request(
        self,
        request: str,
        max_tier: str = "local-large",
        timeout: Optional[int] = None,
        retry_attempts: Optional[int] = None,
    ) -> None:
        """
        Process a request using the Smart Responder Chain.

        Args:
            request: The request to process
            max_tier: Maximum processing tier to use
            timeout: Processing timeout in seconds
            retry_attempts: Number of retry attempts
        """
        self._log_operation(
            "process_request",
            request=request[:100] + "..." if len(request) > 100 else request,
            max_tier=max_tier,
        )

        # Validate tier
        valid_tiers = [
            "local-small",
            "local-medium",
            "local-large",
            "local-huge",
            "cloud-gpt",
            "cloud-claude",
        ]
        if max_tier not in valid_tiers:
            self._output_result(
                f"Invalid tier. Must be one of: {', '.join(valid_tiers)}", success=False
            )
            sys.exit(1)

        timeout = timeout or self.config.tiers.timeout_seconds
        retry_attempts = retry_attempts or self.config.tiers.retry_attempts

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=not self.config.output.progress_bars,
        ) as progress:

            task = progress.add_task("Processing request...", total=None)

            try:
                # Initialize processing chain
                progress.update(
                    task, description="Initializing Smart Responder Chain..."
                )
                chain = await self._initialize_processing_chain(max_tier)

                # Process the request
                progress.update(task, description=f"Processing with {max_tier} tier...")
                result = await self._execute_processing(
                    chain, request, timeout, retry_attempts
                )

                # Format and output result
                self._output_result(
                    {
                        "request": request,
                        "tier_used": result.get("tier_used", max_tier),
                        "processing_time": result.get("processing_time", 0),
                        "result": result.get("content", ""),
                        "metadata": result.get("metadata", {}),
                    }
                )

            except asyncio.TimeoutError:
                self._output_result(
                    f"Processing timed out after {timeout} seconds", success=False
                )
                sys.exit(1)
            except Exception as e:
                self._output_result(f"Processing failed: {e}", success=False)
                sys.exit(1)

    async def _initialize_processing_chain(self, max_tier: str) -> Any:
        """Initialize the Smart Responder Chain for processing."""
        # This would integrate with the actual Smart Responder Chain implementation
        # For now, we'll create a mock implementation

        class MockProcessingChain:
            def __init__(self, max_tier: str):
                self.max_tier = max_tier

        return MockProcessingChain(max_tier)

    async def _execute_processing(
        self, chain: Any, request: str, timeout: int, retry_attempts: int
    ) -> Dict[str, Any]:
        """Execute processing with the given chain."""
        import time

        start_time = time.time()

        # Mock processing - replace with actual implementation
        await asyncio.sleep(1)  # Simulate processing time

        processing_time = time.time() - start_time

        return {
            "tier_used": chain.max_tier,
            "processing_time": round(processing_time, 2),
            "content": f"Processed: {request}",
            "metadata": {
                "retry_attempts_used": 0,
                "model_version": "mock-v1.0",
                "confidence_score": 0.95,
            },
        }


class StatusHandler(BaseHandler):
    """Handler for system status and health monitoring."""

    async def show_status(self, detailed: bool = False) -> None:
        """Show system status and health."""
        self._log_operation("show_status", detailed=detailed)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=not self.config.output.progress_bars,
        ) as progress:

            task = progress.add_task("Checking system status...", total=None)

            try:
                # Check various system components
                status_data = {}

                progress.update(task, description="Checking model availability...")
                status_data["models"] = await self._check_model_availability()

                progress.update(task, description="Checking API services...")
                status_data["api"] = await self._check_api_status()

                progress.update(task, description="Checking database...")
                status_data["database"] = await self._check_database_status()

                if detailed:
                    progress.update(task, description="Checking system resources...")
                    status_data["resources"] = await self._check_system_resources()

                    progress.update(task, description="Checking monitoring...")
                    status_data["monitoring"] = await self._check_monitoring_status()

                # Generate overall status
                overall_status = self._calculate_overall_status(status_data)

                result = {
                    "overall_status": overall_status,
                    "timestamp": self._get_timestamp(),
                    "components": status_data,
                }

                if self.config.output.format == "text":
                    self._display_status_table(result)
                else:
                    self._output_result(result)

            except Exception as e:
                self._output_result(f"Status check failed: {e}", success=False)
                sys.exit(1)

    async def _check_model_availability(self) -> Dict[str, Any]:
        """Check availability of different model tiers."""
        models = {
            "local-small": await self._ping_model(self.config.tiers.local_small),
            "local-medium": await self._ping_model(self.config.tiers.local_medium),
            "local-large": await self._ping_model(self.config.tiers.local_large),
            "local-huge": await self._ping_model(self.config.tiers.local_huge),
            "cloud-gpt": await self._ping_model(self.config.tiers.cloud_gpt),
            "cloud-claude": await self._ping_model(self.config.tiers.cloud_claude),
        }

        available_count = sum(1 for status in models.values() if status["available"])

        return {
            "models": models,
            "available_count": available_count,
            "total_count": len(models),
            "status": "healthy" if available_count > 0 else "unhealthy",
        }

    async def _ping_model(self, model_name: str) -> Dict[str, Any]:
        """Ping a specific model to check availability."""
        try:
            # Mock implementation - replace with actual model ping
            await asyncio.sleep(0.1)
            return {"available": True, "response_time": 0.1, "version": "1.0.0"}
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "response_time": None,
                "version": None,
            }

    async def _check_api_status(self) -> Dict[str, Any]:
        """Check API server status."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"http://{self.config.api.host}:{self.config.api.port}/health"
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "response_time": 0.1,  # Mock value
                            "endpoint": url,
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}",
                            "endpoint": url,
                        }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e),
                "endpoint": f"http://{self.config.api.host}:{self.config.api.port}",
            }

    async def _check_database_status(self) -> Dict[str, Any]:
        """Check database connectivity and status."""
        try:
            # Mock database check - replace with actual database ping
            await asyncio.sleep(0.1)
            return {
                "status": "healthy",
                "response_time": 0.1,
                "connection_pool": "10/10 active",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_pool": "0/10 active",
            }

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "load_average": list(psutil.getloadavg()),
                "status": "healthy",
            }
        except ImportError:
            return {"status": "unavailable", "error": "psutil not installed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_monitoring_status(self) -> Dict[str, Any]:
        """Check monitoring services status."""
        monitoring = {}

        if self.config.monitoring.prometheus_enabled:
            monitoring["prometheus"] = await self._check_prometheus()

        if self.config.monitoring.jaeger_enabled:
            monitoring["jaeger"] = await self._check_jaeger()

        if self.config.monitoring.sentry_enabled:
            monitoring["sentry"] = await self._check_sentry()

        return monitoring

    async def _check_prometheus(self) -> Dict[str, Any]:
        """Check Prometheus metrics endpoint."""
        try:
            # Mock Prometheus check
            return {"status": "healthy", "metrics_count": 156}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_jaeger(self) -> Dict[str, Any]:
        """Check Jaeger tracing."""
        try:
            # Mock Jaeger check
            return {"status": "healthy", "traces_count": 1024}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_sentry(self) -> Dict[str, Any]:
        """Check Sentry error tracking."""
        try:
            # Mock Sentry check
            return {"status": "healthy", "errors_count": 0}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _calculate_overall_status(self, status_data: Dict[str, Any]) -> str:
        """Calculate overall system health status."""
        critical_components = ["models", "api"]

        for component in critical_components:
            if component in status_data:
                comp_status = status_data[component].get("status", "unknown")
                if comp_status in ["unhealthy", "unavailable", "error"]:
                    return "unhealthy"

        return "healthy"

    def _display_status_table(self, status_data: Dict[str, Any]) -> None:
        """Display status as a formatted table."""
        table = Table(title="ONEX System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")

        # Add overall status
        overall = status_data["overall_status"]
        status_color = "green" if overall == "healthy" else "red"
        table.add_row(
            "Overall", f"[{status_color}]{overall.upper()}[/{status_color}]", ""
        )

        # Add component details
        components = status_data["components"]

        if "models" in components:
            models = components["models"]
            available = models["available_count"]
            total = models["total_count"]
            table.add_row("Models", f"{available}/{total} available", "")

        if "api" in components:
            api = components["api"]
            status = api["status"]
            details = f"Response: {api.get('response_time', 'N/A')}s"
            table.add_row("API", status, details)

        if "database" in components:
            db = components["database"]
            status = db["status"]
            details = db.get("connection_pool", "")
            table.add_row("Database", status, details)

        self.console.print(table)


class ConfigHandler(BaseHandler):
    """Handler for configuration management operations."""

    def init_config(self, force: bool = False) -> None:
        """Initialize default configuration."""
        config_path = CLIConfig.get_default_config_path()

        if config_path.exists() and not force:
            self._output_result(
                "Configuration already exists. Use --force to overwrite.", success=False
            )
            return

        try:
            config = CLIConfig()
            config.create_directories()
            config.to_file(config_path)

            self._output_result(f"Configuration initialized at {config_path}")

            # Show key settings
            if self.config.output.format == "text":
                self.console.print("\n[bold]Key Settings:[/bold]")
                self.console.print(f"Config directory: {config.config_dir}")
                self.console.print(f"Data directory: {config.data_dir}")
                self.console.print(
                    f"API endpoint: http://{config.api.host}:{config.api.port}"
                )

        except Exception as e:
            self._output_result(
                f"Failed to initialize configuration: {e}", success=False
            )
            sys.exit(1)

    def show_config(self, section: Optional[str] = None) -> None:
        """Show current configuration."""
        try:
            config_dict = self.config.model_dump()

            if section:
                if section not in config_dict:
                    self._output_result(
                        f"Configuration section '{section}' not found", success=False
                    )
                    return
                config_dict = {section: config_dict[section]}

            self._output_result(config_dict)

        except Exception as e:
            self._output_result(f"Failed to show configuration: {e}", success=False)
            sys.exit(1)

    def validate_config(self) -> None:
        """Validate current configuration."""
        try:
            # Attempt to create directories
            self.config.create_directories()

            errors = []
            warnings = []

            # Validate API configuration
            if not (1024 <= self.config.api.port <= 65535):
                errors.append(f"Invalid API port: {self.config.api.port}")

            # Validate database URL
            if not self.config.database.url.startswith(("postgresql://", "sqlite://")):
                warnings.append(
                    "Database URL should use postgresql:// or sqlite:// scheme"
                )

            # Validate monitoring configuration
            if self.config.monitoring.prometheus_enabled:
                if not (1024 <= self.config.monitoring.prometheus_port <= 65535):
                    errors.append(
                        f"Invalid Prometheus port: {self.config.monitoring.prometheus_port}"
                    )

            # Check directory permissions
            for dir_name, directory in [
                ("config", self.config.config_dir),
                ("data", self.config.data_dir),
                ("cache", self.config.cache_dir),
            ]:
                if not directory.exists():
                    warnings.append(f"{dir_name} directory does not exist: {directory}")
                elif not os.access(directory, os.W_OK):
                    errors.append(
                        f"No write permission for {dir_name} directory: {directory}"
                    )

            # Generate validation result
            validation_result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "config_path": str(CLIConfig.get_default_config_path()),
            }

            if self.config.output.format == "text":
                if validation_result["valid"]:
                    self.console.print("✅ Configuration is valid", style="green")
                else:
                    self.console.print("❌ Configuration has errors", style="red")

                if errors:
                    self.console.print("\n[bold red]Errors:[/bold red]")
                    for error in errors:
                        self.console.print(f"  • {error}")

                if warnings:
                    self.console.print("\n[bold yellow]Warnings:[/bold yellow]")
                    for warning in warnings:
                        self.console.print(f"  • {warning}")
            else:
                self._output_result(
                    validation_result, success=validation_result["valid"]
                )

        except Exception as e:
            self._output_result(f"Configuration validation failed: {e}", success=False)
            sys.exit(1)
