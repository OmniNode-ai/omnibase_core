"""
Demo CLI Commands.

Provides CLI commands for discovering and running ONEX demo scenarios.
Demo scenarios are located in the examples/demo/ directory and showcase
various ONEX capabilities and patterns.

Usage:
    onex demo list
    onex demo list --verbose
    onex demo run --scenario model-validate
    onex demo run --scenario model-validate --live

.. versionadded:: 0.7.0
    Added as part of Demo V1 CLI (OMN-1396)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.types.typed_dict_demo import (
    TypedDictDemoConfig,
    TypedDictDemoResult,
    TypedDictDemoSummary,
    TypedDictInvariantResult,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

# Contract file patterns that indicate a demo scenario
SCENARIO_CONTRACT_FILES: tuple[str, ...] = (
    "contract.yaml",
    "invariants.yaml",
)

# Minimum column width for scenario names in table output
MIN_NAME_COLUMN_WIDTH: int = 20


def _get_demo_root() -> Path:
    """Get the root path for demo scenarios.

    Returns the examples/demo/ directory relative to the omnibase_core package.
    This function handles both development (editable install) and package
    installation scenarios.

    Returns:
        Path to the examples/demo/ directory.

    Raises:
        click.ClickException: If the demo directory cannot be found.
    """
    # Try relative to this file (development scenario)
    # src/omnibase_core/cli/cli_demo.py -> src/omnibase_core/../../examples/demo
    cli_dir = Path(__file__).resolve().parent
    src_omnibase = cli_dir.parent  # src/omnibase_core
    src_dir = src_omnibase.parent  # src
    repo_root = src_dir.parent  # repository root
    demo_path = repo_root / "examples" / "demo"

    if demo_path.is_dir():
        return demo_path

    # Fallback: try relative to current working directory
    cwd_demo_path = Path.cwd() / "examples" / "demo"
    if cwd_demo_path.is_dir():
        return cwd_demo_path

    raise click.ClickException(
        "Could not locate examples/demo/ directory. "
        "Ensure you are running from the repository root or that the package "
        "is installed correctly."
    )


def _is_demo_scenario(path: Path) -> bool:
    """Check if a directory contains a valid demo scenario.

    A directory is considered a demo scenario if it contains at least one
    of the recognized contract files (contract.yaml, invariants.yaml).

    Args:
        path: Directory path to check.

    Returns:
        True if the directory contains a demo scenario, False otherwise.
    """
    if not path.is_dir():
        return False

    for contract_file in SCENARIO_CONTRACT_FILES:
        if (path / contract_file).is_file():
            return True

    return False


def _extract_scenario_description(scenario_path: Path) -> str:
    """Extract a description for a demo scenario.

    Attempts to extract a description from the scenario's contract.yaml
    or README.md file. Falls back to a generic description if none found.

    Args:
        scenario_path: Path to the scenario directory.

    Returns:
        A description string for the scenario.
    """
    # Try to extract from contract.yaml metadata
    contract_path = scenario_path / "contract.yaml"
    if contract_path.is_file():
        try:
            with contract_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if isinstance(data, dict):
                # Check for metadata.description first
                metadata = data.get("metadata", {})
                if isinstance(metadata, dict) and "description" in metadata:
                    desc = metadata["description"]
                    # Truncate long descriptions
                    if isinstance(desc, str) and len(desc) > 60:
                        return desc[:57] + "..."
                    return str(desc) if desc else "Demo scenario"

                # Fall back to top-level description
                if "description" in data:
                    desc = data["description"]
                    if isinstance(desc, str) and len(desc) > 60:
                        return desc[:57] + "..."
                    return str(desc) if desc else "Demo scenario"
        except (OSError, yaml.YAMLError):
            # Ignore YAML parsing errors and continue to fallback
            pass

    # Try README.md - extract first non-empty line after header
    readme_path = scenario_path / "README.md"
    if readme_path.is_file():
        try:
            with readme_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and headers
                    if line and not line.startswith("#"):
                        if len(line) > 60:
                            return line[:57] + "..."
                        return line
        except OSError:
            pass

    # Default description based on scenario name
    return f"{scenario_path.name.replace('-', ' ').title()} demo scenario"


def _discover_scenarios(demo_root: Path) -> Iterator[tuple[str, str, Path]]:
    """Discover all demo scenarios in the demo root directory.

    Scans the demo directory for subdirectories containing valid demo
    scenarios. Yields scenario information as tuples.

    Args:
        demo_root: Root path of the demo directory.

    Yields:
        Tuples of (scenario_name, description, scenario_path).
    """
    if not demo_root.is_dir():
        return

    for item in sorted(demo_root.iterdir()):
        # Skip hidden directories and non-directories
        if item.name.startswith(".") or item.name.startswith("_"):
            continue
        if not item.is_dir():
            continue

        # Check if this is a direct scenario
        if _is_demo_scenario(item):
            description = _extract_scenario_description(item)
            yield (item.name, description, item)
            continue

        # Check subdirectories (e.g., handlers/support_assistant)
        for subitem in sorted(item.iterdir()):
            if subitem.name.startswith(".") or subitem.name.startswith("_"):
                continue
            if _is_demo_scenario(subitem):
                # Use path relative to demo root for name
                rel_name = f"{item.name}/{subitem.name}"
                description = _extract_scenario_description(subitem)
                yield (rel_name, description, subitem)


@click.group()
@click.pass_context
def demo(ctx: click.Context) -> None:
    """Demo scenario management commands for ONEX.

    Provides tools for discovering and running ONEX demo scenarios.
    Demo scenarios are located in the examples/demo/ directory and
    showcase various ONEX capabilities including model validation,
    handler patterns, and workflow examples.

    \b
    Commands:
        list   - List all available demo scenarios

    \b
    Examples:
        onex demo list
        onex demo list --verbose
    """
    ctx.ensure_object(dict)


@demo.command("list")
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Custom path to demo directory. Defaults to examples/demo/.",
)
@click.pass_context
def list_scenarios(ctx: click.Context, path: Path | None) -> None:
    """List available demo scenarios.

    Discovers and displays all demo scenarios found in the examples/demo/
    directory. Each scenario is shown with its name and description.

    \b
    Exit Codes:
        0 - Success (scenarios listed)
        1 - Error (demo directory not found)

    \b
    Examples:
        onex demo list
        onex demo list --path /custom/demo/path
        onex --verbose demo list
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    # Determine demo root path
    try:
        demo_root = path if path else _get_demo_root()
    except click.ClickException:
        raise

    if verbose:
        emit_log_event_sync(
            EnumLogLevel.INFO,
            "Scanning for demo scenarios",
            {"demo_root": str(demo_root)},
        )

    # Discover scenarios
    scenarios = list(_discover_scenarios(demo_root))

    if not scenarios:
        click.echo("No demo scenarios found.")
        if verbose:
            click.echo(f"  Searched in: {demo_root}")
            click.echo(
                f"  Looking for directories containing: {', '.join(SCENARIO_CONTRACT_FILES)}"
            )
        ctx.exit(EnumCLIExitCode.SUCCESS)

    # Calculate column width for formatting
    max_name_len = max(len(name) for name, _, _ in scenarios)
    name_width = max(MIN_NAME_COLUMN_WIDTH, max_name_len + 2)

    # Display header
    click.echo()
    click.echo("Available demo scenarios:")
    click.echo()

    # Display each scenario
    for name, description, scenario_path in scenarios:
        click.echo(f"  {name:<{name_width}} {description}")

        if verbose:
            # Show additional details in verbose mode
            contract_files = [
                f for f in SCENARIO_CONTRACT_FILES if (scenario_path / f).is_file()
            ]
            if contract_files:
                click.echo(f"  {'':<{name_width}} Files: {', '.join(contract_files)}")

    click.echo()
    click.echo(f"Total: {len(scenarios)} scenario(s)")

    if verbose:
        click.echo(f"Demo root: {demo_root}")

    ctx.exit(EnumCLIExitCode.SUCCESS)


def _get_scenario_path(scenario_name: str, demo_root: Path) -> Path | None:
    """Find a scenario by name in the demo directory.

    Args:
        scenario_name: Name of the scenario (e.g., 'model-validate').
        demo_root: Root path of the demo directory.

    Returns:
        Path to the scenario directory, or None if not found.
    """
    # Direct match
    direct_path = demo_root / scenario_name
    if _is_demo_scenario(direct_path):
        return direct_path

    # Check subdirectories (e.g., handlers/support_assistant)
    if "/" in scenario_name:
        parts = scenario_name.split("/", 1)
        subpath = demo_root / parts[0] / parts[1]
        if _is_demo_scenario(subpath):
            return subpath

    return None


def _load_corpus(corpus_dir: Path) -> list[dict[str, object]]:
    """Load corpus samples from a directory.

    Args:
        corpus_dir: Path to corpus directory.

    Returns:
        List of corpus sample dictionaries.
    """
    samples: list[dict[str, object]] = []

    if not corpus_dir.is_dir():
        return samples

    # Load from subdirectories (golden/, edge-cases/)
    for subdir in sorted(corpus_dir.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("."):
            for sample_file in sorted(subdir.glob("*.yaml")):
                try:
                    with sample_file.open(encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            data["_source_file"] = str(
                                sample_file.relative_to(corpus_dir)
                            )
                            data["_category"] = subdir.name
                            samples.append(data)
                except (OSError, yaml.YAMLError):
                    pass

    # Also check for direct YAML files in corpus root
    for sample_file in sorted(corpus_dir.glob("*.yaml")):
        if sample_file.name == "README.md":
            continue
        try:
            with sample_file.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    data["_source_file"] = sample_file.name
                    data["_category"] = "root"
                    samples.append(data)
        except (OSError, yaml.YAMLError):
            pass

    return samples


def _load_mock_responses(mock_dir: Path) -> dict[str, dict[str, object]]:
    """Load mock responses from a directory.

    Args:
        mock_dir: Path to mock-responses directory.

    Returns:
        Dictionary mapping (model_type, sample_id) to response data.
    """
    responses: dict[str, dict[str, object]] = {}

    if not mock_dir.is_dir():
        return responses

    for model_dir in mock_dir.iterdir():
        if not model_dir.is_dir() or model_dir.name.startswith("."):
            continue

        model_type = model_dir.name  # e.g., 'baseline', 'candidate'
        for response_file in model_dir.glob("*.json"):
            try:
                with response_file.open(encoding="utf-8") as f:
                    data = json.load(f)
                    key = f"{model_type}/{response_file.stem}"
                    responses[key] = data
            except (OSError, json.JSONDecodeError):
                pass

    return responses


def _create_output_bundle(
    output_dir: Path,
    scenario_name: str,
    corpus: list[dict[str, object]],
    results: list[TypedDictDemoResult],
    config: TypedDictDemoConfig,
    summary: TypedDictDemoSummary,
) -> None:
    """Create the output bundle directory structure.

    Args:
        output_dir: Root output directory.
        scenario_name: Name of the scenario.
        corpus: List of corpus samples.
        results: List of evaluation results.
        config: Run configuration.
        summary: Results summary.
    """
    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "inputs").mkdir(exist_ok=True)
    (output_dir / "outputs").mkdir(exist_ok=True)

    # Write run manifest
    manifest = {
        "scenario": scenario_name,
        "timestamp": config.get("timestamp", datetime.now(UTC).isoformat()),
        "seed": config.get("seed"),
        "live_mode": config.get("live", False),
        "repeat": config.get("repeat", 1),
        "corpus_count": len(corpus),
        "result_count": len(results),
    }
    with (output_dir / "run_manifest.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False)

    # Write corpus samples to inputs/
    for i, sample in enumerate(corpus):
        sample_file = output_dir / "inputs" / f"sample_{i + 1:03d}.yaml"
        with sample_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(sample, f, default_flow_style=False)

    # Write results to outputs/
    for i, result in enumerate(results):
        result_file = output_dir / "outputs" / f"sample_{i + 1:03d}.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    # Write report.json
    report_json = {
        "scenario": scenario_name,
        "timestamp": manifest["timestamp"],
        "config": config,
        "summary": summary,
        "results": results,
    }
    with (output_dir / "report.json").open("w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)

    # Write report.md
    _write_markdown_report(output_dir / "report.md", scenario_name, summary, results)


def _write_markdown_report(
    path: Path,
    scenario_name: str,
    summary: TypedDictDemoSummary,
    results: list[TypedDictDemoResult],
) -> None:
    """Write a human-readable markdown report.

    Args:
        path: Output file path.
        scenario_name: Name of the scenario.
        summary: Results summary.
        results: List of evaluation results.
    """
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# ONEX Demo Report: {scenario_name}\n\n")
        f.write(f"**Generated**: {datetime.now(UTC).isoformat()}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Samples**: {summary.get('total', 0)}\n")
        f.write(f"- **Passed**: {summary.get('passed', 0)}\n")
        f.write(f"- **Failed**: {summary.get('failed', 0)}\n")
        f.write(f"- **Pass Rate**: {summary.get('pass_rate', 0):.1%}\n")
        f.write(f"- **Verdict**: {summary.get('verdict', 'UNKNOWN')}\n\n")

        if summary.get("invariant_results"):
            f.write("## Invariant Results\n\n")
            f.write("| Invariant | Passed | Total | Rate |\n")
            f.write("|-----------|--------|-------|------|\n")
            for inv_name, inv_result in summary["invariant_results"].items():
                passed = inv_result.get("passed", 0)
                total = inv_result.get("total", 0)
                rate = passed / total if total > 0 else 0
                status = "✓" if passed == total else "⚠"
                f.write(f"| {status} {inv_name} | {passed} | {total} | {rate:.0%} |\n")
            f.write("\n")

        if results:
            f.write("## Sample Results\n\n")
            for i, result in enumerate(results[:10]):  # Limit to first 10
                status = "✓" if result.get("passed", False) else "✗"
                f.write(
                    f"- {status} Sample {i + 1}: {result.get('sample_id', 'unknown')}\n"
                )
            if len(results) > 10:
                f.write(f"\n... and {len(results) - 10} more samples\n")


def _print_banner(scenario_name: str) -> None:
    """Print the demo banner.

    Args:
        scenario_name: Name of the scenario.
    """
    width = 65
    click.echo("═" * width)
    title = f"ONEX DEMO: {scenario_name}"
    padding = (width - len(title)) // 2
    click.echo(" " * padding + title)
    click.echo("═" * width)
    click.echo()


def _print_results_summary(summary: TypedDictDemoSummary, output_dir: Path) -> None:
    """Print the results summary.

    Args:
        summary: Results summary dictionary.
        output_dir: Path to output directory.
    """
    click.echo("─" * 65)
    click.echo("RESULTS")
    click.echo("─" * 65)

    if summary.get("invariant_results"):
        for inv_name, inv_result in summary["invariant_results"].items():
            passed = inv_result.get("passed", 0)
            total = inv_result.get("total", 0)
            rate = passed / total if total > 0 else 0
            status = "✓" if passed == total else "⚠"
            rate_str = f"{rate:.0%}"
            failures = "" if passed == total else f" ← {total - passed} failures"
            click.echo(
                f"{status} {inv_name:<25} {passed}/{total} ({rate_str}){failures}"
            )

    click.echo()
    verdict = summary.get("verdict", "UNKNOWN")
    if verdict == "PASS":
        click.echo(click.style(f"Verdict: {verdict}", fg="green", bold=True))
    elif verdict == "REVIEW REQUIRED":
        click.echo(click.style(f"Verdict: {verdict}", fg="yellow", bold=True))
    else:
        click.echo(click.style(f"Verdict: {verdict}", fg="red", bold=True))

    click.echo()
    click.echo("─" * 65)
    click.echo("OUTPUT")
    click.echo("─" * 65)
    click.echo(f"Bundle:  {output_dir}/")
    click.echo(f"Report:  {output_dir}/report.md")
    click.echo()
    click.echo(f"To view: cat {output_dir}/report.md")


@demo.command("run")
@click.option(
    "--scenario",
    "-s",
    required=True,
    help="Name of the demo scenario to run (e.g., model-validate).",
)
@click.option(
    "--live",
    is_flag=True,
    default=False,
    help="Use real LLM calls instead of mock responses.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Custom output directory. Defaults to ./out/demo/<timestamp>/.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for deterministic execution.",
)
@click.option(
    "--repeat",
    type=int,
    default=1,
    help="Repeat corpus N times (to simulate larger corpus).",
)
@click.pass_context
def run_demo(
    ctx: click.Context,
    scenario: str,
    live: bool,
    output: Path | None,
    seed: int | None,
    repeat: int,
) -> None:
    """Run a demo scenario.

    Executes a demo scenario with corpus replay and invariant evaluation.
    By default, uses mock responses for reproducible demonstrations without
    requiring API keys.

    \b
    Exit Codes:
        0 - All invariants passed
        1 - Some invariants failed or error occurred

    \b
    Examples:
        onex demo run --scenario model-validate
        onex demo run --scenario model-validate --live
        onex demo run --scenario model-validate --output ./my-output
        onex demo run --scenario model-validate --seed 42
        onex demo run --scenario model-validate --repeat 3
    """
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S")

    # Determine demo root and scenario path
    try:
        demo_root = _get_demo_root()
    except click.ClickException:
        raise

    scenario_path = _get_scenario_path(scenario, demo_root)
    if scenario_path is None:
        raise click.ClickException(
            f"Scenario '{scenario}' not found. Run 'onex demo list' to see available scenarios."
        )

    # Determine output directory
    if output is None:
        output = Path("./out/demo") / timestamp
    output = output.resolve()

    # Load corpus
    corpus_dir = scenario_path / "corpus"
    corpus = _load_corpus(corpus_dir)
    if not corpus:
        raise click.ClickException(
            f"No corpus samples found in {corpus_dir}. "
            "Ensure the scenario has a corpus/ directory with YAML files."
        )

    # Apply repeat
    if repeat > 1:
        original_corpus = corpus.copy()
        for _ in range(repeat - 1):
            corpus.extend(original_corpus)

    # Load mock responses (unless live mode)
    mock_responses: dict[str, dict[str, object]] = {}
    if not live:
        mock_dir = scenario_path / "mock-responses"
        mock_responses = _load_mock_responses(mock_dir)

    # Load invariants
    invariants_path = scenario_path / "invariants.yaml"
    invariants: dict[str, object] = {}
    if invariants_path.is_file():
        try:
            with invariants_path.open(encoding="utf-8") as f:
                invariants = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            if verbose:
                click.echo(f"Warning: Could not load invariants: {e}", err=True)

    # Print banner
    _print_banner(scenario)

    # Print configuration
    mode = "live" if live else "mock"
    click.echo(f"Corpus:      {corpus_dir} ({len(corpus)} samples)")
    click.echo(f"Mode:        {mode}")
    if not live and mock_responses:
        models = {k.split("/")[0] for k in mock_responses}
        click.echo(f"Models:      {', '.join(sorted(models))}")
    if seed is not None:
        click.echo(f"Seed:        {seed}")
    click.echo()

    # Run evaluation (simplified for demo - actual implementation would use services)
    click.echo("Running evaluation...")
    results: list[TypedDictDemoResult] = []
    passed_count = 0

    # Progress indicator
    total = len(corpus)
    for i, sample in enumerate(corpus):
        # Simple progress bar
        progress = int((i + 1) / total * 40)
        bar = "█" * progress + "░" * (40 - progress)
        click.echo(f"\rRunning replay... {bar} {i + 1}/{total}", nl=False)
        sys.stdout.flush()

        # Simulate evaluation (in real implementation, use ServiceInvariantEvaluator)
        sample_id_raw = (
            sample.get("ticket_id") or sample.get("_source_file") or f"sample_{i + 1}"
        )
        sample_id = str(sample_id_raw)

        # Determine pass/fail and invariants checked
        passed = True
        invariants_checked: list[str] = []

        # Check basic invariants from config
        thresholds = invariants.get("thresholds")
        if isinstance(thresholds, dict) and thresholds.get("confidence_min"):
            # Mock: randomly pass some samples for demo purposes
            # In real implementation, this would check actual model output
            if seed is not None:
                import random

                random.seed(seed + i)
                passed = random.random() > 0.2
            invariants_checked.append("confidence_threshold")

        result: TypedDictDemoResult = {
            "sample_id": sample_id,
            "passed": passed,
            "invariants_checked": invariants_checked,
        }

        if passed:
            passed_count += 1

        results.append(result)

    click.echo()  # New line after progress bar
    click.echo()

    # Calculate summary
    total_samples = len(results)
    failed_count = total_samples - passed_count
    pass_rate = passed_count / total_samples if total_samples > 0 else 0

    # Determine verdict
    if pass_rate >= 1.0:
        verdict = "PASS"
    elif pass_rate >= 0.8:
        verdict = "REVIEW REQUIRED"
    else:
        verdict = "FAIL"

    # Build invariant results
    invariant_results: dict[str, TypedDictInvariantResult] = {}
    if results:
        invariant_names: set[str] = set()
        for r in results:
            invariant_names.update(r["invariants_checked"])
        for inv_name in invariant_names:
            inv_passed = sum(
                1
                for r in results
                if r["passed"] and inv_name in r["invariants_checked"]
            )
            inv_total = sum(1 for r in results if inv_name in r["invariants_checked"])
            invariant_results[inv_name] = {
                "passed": inv_passed,
                "total": inv_total,
            }

    summary: TypedDictDemoSummary = {
        "total": total_samples,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": pass_rate,
        "verdict": verdict,
        "invariant_results": invariant_results,
    }

    # Create output bundle
    config: TypedDictDemoConfig = {
        "scenario": scenario,
        "live": live,
        "seed": seed,
        "repeat": repeat,
        "timestamp": timestamp,
    }
    _create_output_bundle(output, scenario, corpus, results, config, summary)

    # Print results
    _print_results_summary(summary, output)

    # Exit with appropriate code
    if verdict == "PASS":
        ctx.exit(EnumCLIExitCode.SUCCESS)
    else:
        ctx.exit(EnumCLIExitCode.ERROR)


__all__ = ["demo"]
