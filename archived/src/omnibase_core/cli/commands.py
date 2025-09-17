"""
Production CLI commands for ONEX Smart Responder Chain.

Provides comprehensive command-line interface with Click framework including
type quality analysis, processing operations, system monitoring, and configuration management.
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from .config import ModelCLIConfig as CLIConfig
from .handlers import ConfigHandler, ProcessHandler, StatusHandler, TypeQualityHandler

# Global console for error output
console = Console()


def async_command(f):
    """Decorator to handle async Click commands."""

    def wrapper(*args, **kwargs):
        try:
            return asyncio.run(f(*args, **kwargs))
        except KeyboardInterrupt:
            console.print("\n❌ Operation cancelled by user", style="yellow")
            sys.exit(130)
        except Exception as e:
            console.print(f"\n❌ Unexpected error: {e}", style="red")
            sys.exit(1)

    return wrapper


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, config: Path | None, verbose: bool, debug: bool):
    """
    ONEX Smart Responder Chain - Production CLI Interface.

    Comprehensive toolkit for type quality analysis, processing operations,
    system monitoring, and deployment management.
    """
    # Initialize configuration
    if config:
        try:
            cli_config = CLIConfig.from_file(config)
        except Exception as e:
            console.print(f"❌ Failed to load config from {config}: {e}", style="red")
            sys.exit(1)
    else:
        cli_config = CLIConfig.load_or_create_default()

    # Override settings from CLI options
    if verbose:
        cli_config.output.log_level = "DEBUG"
    if debug:
        cli_config.debug = True
        cli_config.output.log_level = "DEBUG"

    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = cli_config


@cli.command()
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to analyze (file or directory)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (JSON, YAML, or text)",
)
@click.option(
    "--include",
    multiple=True,
    help="File patterns to include (can be used multiple times)",
)
@click.option(
    "--exclude",
    multiple=True,
    help="File patterns to exclude (can be used multiple times)",
)
@click.pass_context
@async_command
async def type_quality(
    ctx,
    path: Path,
    output: Path | None,
    include: tuple,
    exclude: tuple,
):
    """
    Analyze type quality for Python code.

    Performs comprehensive type analysis using mypy and generates detailed
    quality reports with scores, recommendations, and actionable insights.

    Examples:
        omni-agent type-quality --path ./src --output report.json
        omni-agent type-quality --path mymodule.py --include "*.py" --exclude "*test*"
    """
    config = ctx.obj["config"]
    handler = TypeQualityHandler(config)

    include_patterns = list(include) if include else None
    exclude_patterns = list(exclude) if exclude else None

    await handler.analyze_path(path, output, include_patterns, exclude_patterns)


@cli.command()
@click.argument("request", type=str)
@click.option(
    "--max-tier",
    type=click.Choice(
        [
            "local-small",
            "local-medium",
            "local-large",
            "local-huge",
            "cloud-gpt",
            "cloud-claude",
        ],
    ),
    default="local-large",
    help="Maximum processing tier to use",
)
@click.option("--timeout", type=int, help="Processing timeout in seconds")
@click.option("--retry-attempts", type=int, help="Number of retry attempts")
@click.pass_context
@async_command
async def process(
    ctx,
    request: str,
    max_tier: str,
    timeout: int | None,
    retry_attempts: int | None,
):
    """
    Process a request using Smart Responder Chain.

    Executes intelligent processing with automatic tier selection,
    retry logic, and comprehensive result formatting.

    Examples:
        omni-agent process "Fix type issues in user.py" --max-tier local-huge
        omni-agent process "Analyze code quality" --timeout 120 --retry-attempts 5
    """
    config = ctx.obj["config"]
    handler = ProcessHandler(config)

    await handler.process_request(request, max_tier, timeout, retry_attempts)


@cli.command()
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed status including system resources and monitoring",
)
@click.pass_context
@async_command
async def status(ctx, detailed: bool):
    """
    Show system status and health information.

    Displays comprehensive system health including model availability,
    API services, database connectivity, and optional resource monitoring.

    Examples:
        omni-agent status
        omni-agent status --detailed
    """
    config = ctx.obj["config"]
    handler = StatusHandler(config)

    await handler.show_status(detailed)


@cli.group()
def config():
    """Configuration management commands."""


@config.command("init")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def config_init(ctx, force: bool):
    """
    Initialize default configuration file.

    Creates a new configuration file with sensible defaults for all
    system components including API, database, monitoring, and processing tiers.

    Examples:
        omni-agent config init
        omni-agent config init --force
    """
    config = ctx.obj["config"]
    handler = ConfigHandler(config)
    handler.init_config(force)


@config.command("show")
@click.option(
    "--section",
    "-s",
    type=click.Choice(["tiers", "output", "api", "database", "monitoring"]),
    help="Show specific configuration section",
)
@click.pass_context
def config_show(ctx, section: str | None):
    """
    Show current configuration.

    Displays the current configuration settings, optionally filtered
    to a specific section for focused viewing.

    Examples:
        omni-agent config show
        omni-agent config show --section api
    """
    config = ctx.obj["config"]
    handler = ConfigHandler(config)
    handler.show_config(section)


@config.command("validate")
@click.pass_context
def config_validate(ctx):
    """
    Validate current configuration.

    Performs comprehensive validation of configuration settings including
    directory permissions, port availability, and service connectivity.

    Examples:
        omni-agent config validate
    """
    config = ctx.obj["config"]
    handler = ConfigHandler(config)
    handler.validate_config()


@cli.command()
@click.option("--host", default=None, help="API host (overrides config)")
@click.option("--port", type=int, default=None, help="API port (overrides config)")
@click.option("--workers", type=int, default=None, help="Number of worker processes")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.pass_context
def serve(
    ctx,
    host: str | None,
    port: int | None,
    workers: int | None,
    reload: bool,
):
    """
    Start the ONEX API server.

    Launches the FastAPI server with production-ready configuration
    including worker processes, monitoring, and health checks.

    Examples:
        omni-agent serve
        omni-agent serve --host 0.0.0.0 --port 8080 --workers 8
        omni-agent serve --reload  # Development mode
    """
    config = ctx.obj["config"]

    # Override config with CLI options
    api_host = host or config.api.host
    api_port = port or config.api.port
    api_workers = workers or config.api.workers

    try:
        import uvicorn

        # Import the FastAPI app (this would be implemented separately)
        from omnibase_core.api.app import create_app

        app = create_app(config)

        console.print(f"🚀 Starting ONEX API server at http://{api_host}:{api_port}")

        if reload:
            console.print("⚠️  Development mode: auto-reload enabled")
            uvicorn.run(
                "omnibase_core.api.app:create_app",
                host=api_host,
                port=api_port,
                reload=reload,
                factory=True,
            )
        else:
            uvicorn.run(
                app,
                host=api_host,
                port=api_port,
                workers=api_workers,
                access_log=config.debug,
            )

    except ImportError:
        console.print(
            "❌ uvicorn not installed. Install with: pip install uvicorn",
            style="red",
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Failed to start API server: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["development", "staging", "production"]),
    default="development",
    help="Deployment environment",
)
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--replicas", "-r", type=int, default=3, help="Number of replicas")
@click.pass_context
def deploy(ctx, environment: str, namespace: str, replicas: int):
    """
    Deploy ONEX to Kubernetes.

    Generates and applies Kubernetes manifests for production deployment
    with configurable scaling, monitoring, and environment settings.

    Examples:
        omni-agent deploy --environment production --namespace onex --replicas 5
        omni-agent deploy --environment staging
    """
    config = ctx.obj["config"]

    console.print(f"🚀 Deploying ONEX to {environment} environment...")
    console.print(f"📦 Namespace: {namespace}")
    console.print(f"🔄 Replicas: {replicas}")

    try:
        # This would integrate with actual Kubernetes deployment logic
        from omnibase_core.deployment.kubernetes import KubernetesDeployer

        deployer = KubernetesDeployer(config)
        deployment_result = deployer.deploy(environment, namespace, replicas)

        if deployment_result.success:
            console.print("✅ Deployment successful!", style="green")
            console.print(f"🌐 Service URL: {deployment_result.service_url}")
        else:
            console.print(
                f"❌ Deployment failed: {deployment_result.error}",
                style="red",
            )
            sys.exit(1)

    except ImportError:
        console.print(
            "❌ Kubernetes client not available. Install with: pip install kubernetes",
            style="red",
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Deployment failed: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["prometheus", "json", "text"]),
    default="text",
    help="Metrics output format",
)
@click.option(
    "--interval",
    "-i",
    type=int,
    default=60,
    help="Metrics collection interval in seconds",
)
@click.pass_context
@async_command
async def metrics(ctx, format: str, interval: int):
    """
    Collect and display system metrics.

    Gathers comprehensive performance and health metrics from all
    system components with configurable output formats.

    Examples:
        omni-agent metrics
        omni-agent metrics --format prometheus --interval 30
    """
    config = ctx.obj["config"]

    console.print(f"📊 Collecting metrics (format: {format}, interval: {interval}s)")

    try:
        # This would integrate with actual metrics collection
        from omnibase_core.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(config)
        metrics_data = await collector.collect_metrics()

        if format == "prometheus":
            output = collector.format_prometheus(metrics_data)
        elif format == "json":
            import json

            output = json.dumps(metrics_data, indent=2, default=str)
        else:
            output = collector.format_text(metrics_data)

        click.echo(output)

    except ImportError:
        console.print(
            "❌ Metrics collection not available. Install monitoring dependencies.",
            style="red",
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Metrics collection failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def version():
    """Show ONEX version information."""
    try:
        # Get version from package metadata
        import importlib.metadata

        version = importlib.metadata.version("omnibase_core")
    except Exception:
        version = "unknown"

    console.print(f"ONEX Smart Responder Chain v{version}")
    console.print("Production CLI Interface")
    console.print("Copyright © 2024 OmniNode Team")


if __name__ == "__main__":
    cli()
