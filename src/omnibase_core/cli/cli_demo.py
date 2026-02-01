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
from typing import TYPE_CHECKING, cast

import click
import yaml

from omnibase_core.decorators.decorator_error_handling import (
    io_error_handling,
    standard_error_handling,
)
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_demo_verdict import EnumDemoVerdict
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.errors.exception_groups import (
    FILE_IO_ERRORS,
    JSON_PARSING_ERRORS,
    YAML_PARSING_ERRORS,
)
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.demo import (
    ModelDemoConfig,
    ModelDemoSummary,
    ModelDemoValidationReport,
    ModelFailureDetail,
    ModelInvariantResult,
    ModelSampleResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

# Contract file patterns that indicate a demo scenario
SCENARIO_CONTRACT_FILES: tuple[str, ...] = (
    "contract.yaml",
    "invariants.yaml",
)

# Minimum column width for scenario names in table output
MIN_NAME_COLUMN_WIDTH: int = 20

# Maximum description length before truncation (truncate at -3 for "...")
# Set high enough to show most descriptions fully while preventing layout issues
MAX_DESCRIPTION_LENGTH: int = 140

# Verdict thresholds for pass rate evaluation
PASS_THRESHOLD: float = 1.0  # 100% pass rate required for PASS
REVIEW_THRESHOLD: float = 0.8  # 80%+ pass rate triggers REVIEW REQUIRED

# Maximum samples to include in markdown report details
MAX_REPORT_SAMPLES: int = 10


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


@standard_error_handling("Demo scenario check")
def _is_demo_scenario(path: Path) -> bool:
    """Check if a directory contains a valid demo scenario.

    A directory is considered a demo scenario if it contains at least one
    of the recognized contract files (contract.yaml, invariants.yaml).

    Args:
        path: Directory path to check.

    Returns:
        True if the directory contains a demo scenario, False otherwise.

    Raises:
        ModelOnexError: If path operations fail (e.g., permission denied).
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
                    if isinstance(desc, str) and len(desc) > MAX_DESCRIPTION_LENGTH:
                        return desc[: MAX_DESCRIPTION_LENGTH - 3] + "..."
                    return str(desc) if desc else "Demo scenario"

                # Fall back to top-level description
                if "description" in data:
                    desc = data["description"]
                    if isinstance(desc, str) and len(desc) > MAX_DESCRIPTION_LENGTH:
                        return desc[: MAX_DESCRIPTION_LENGTH - 3] + "..."
                    return str(desc) if desc else "Demo scenario"
        except (*FILE_IO_ERRORS, *YAML_PARSING_ERRORS):
            # fallback-ok: use default description if contract file is unreadable or malformed
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
                        if len(line) > MAX_DESCRIPTION_LENGTH:
                            return line[: MAX_DESCRIPTION_LENGTH - 3] + "..."
                        return line
        except FILE_IO_ERRORS:
            # fallback-ok: use default description if README is unreadable
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
    demo_root = path if path else _get_demo_root()

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


def _is_path_within_root(path: Path, root: Path) -> bool:
    """Check if a path is safely within a root directory.

    Validates that the resolved path doesn't escape the root via path traversal
    (e.g., '../../../etc/passwd').

    Args:
        path: Path to validate.
        root: Root directory that path must be within.

    Returns:
        True if path is within root, False otherwise.
    """
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        # Check if the resolved path starts with the resolved root
        return resolved_path.is_relative_to(resolved_root)
    except (OSError, ValueError):
        return False


@standard_error_handling("Scenario path resolution")
def _get_scenario_path(scenario_name: str, demo_root: Path) -> Path | None:
    """Resolve scenario name to path, supporting nested names like 'handlers/foo'.

    Args:
        scenario_name: Name of the scenario (e.g., 'model-validate' or 'handlers/foo').
        demo_root: Root path of the demo directory.

    Returns:
        Path to the scenario directory if found, None otherwise.
        Returns None if path traversal is detected (path escapes demo root).

    Raises:
        ModelOnexError: If path operations fail (e.g., permission denied).
    """
    # Direct match
    direct_path = demo_root / scenario_name
    # Security: validate path doesn't escape demo root
    if not _is_path_within_root(direct_path, demo_root):
        return None
    if _is_demo_scenario(direct_path):
        return direct_path

    # Check subdirectories (e.g., handlers/support_assistant)
    if "/" in scenario_name:
        parts = scenario_name.split("/", 1)
        subpath = demo_root / parts[0] / parts[1]
        # Security: validate path doesn't escape demo root
        if not _is_path_within_root(subpath, demo_root):
            return None
        if _is_demo_scenario(subpath):
            return subpath

    return None


def _load_corpus(corpus_dir: Path, *, verbose: bool = False) -> list[dict[str, object]]:
    """Load YAML samples from corpus directory with metadata injection.

    Scans subdirectories (e.g., golden/, edge-cases/) and root for YAML files,
    injecting _source_file (relative path) and _category (subdirectory name)
    metadata into each sample for traceability during evaluation.

    Args:
        corpus_dir: Path to the corpus directory containing sample YAML files.
        verbose: If True, emit warnings to stderr for unreadable or malformed files.

    Returns:
        List of sample dicts, each with injected _source_file and _category keys.
        Returns empty list if corpus_dir does not exist.
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
                except (*FILE_IO_ERRORS, *YAML_PARSING_ERRORS) as e:
                    # fallback-ok: skip unreadable or malformed corpus files
                    if verbose:
                        click.echo(
                            f"Warning: Could not load corpus file {sample_file}: {e}",
                            err=True,
                        )

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
        except (*FILE_IO_ERRORS, *YAML_PARSING_ERRORS) as e:
            # fallback-ok: skip unreadable or malformed corpus files
            if verbose:
                click.echo(
                    f"Warning: Could not load corpus file {sample_file}: {e}", err=True
                )

    return samples


def _load_mock_responses(
    mock_dir: Path, *, verbose: bool = False
) -> dict[str, dict[str, object]]:
    """Load mock LLM responses from model-specific subdirectories.

    Scans subdirectories named by model type (e.g., baseline/, candidate/) for JSON
    response files. Keys are formatted as 'model_type/sample_stem' for lookup by
    _find_mock_response_by_ticket_id.

    Args:
        mock_dir: Path to mock-responses directory containing model subdirs.
        verbose: If True, emit warnings to stderr for unreadable or malformed files.

    Returns:
        Dict mapping 'model_type/sample_stem' to response data.
        Returns empty dict if mock_dir does not exist.
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
                    # Guard against non-dict JSON payloads (e.g., arrays, strings)
                    if isinstance(data, dict):
                        key = f"{model_type}/{response_file.stem}"
                        responses[key] = data
            except (*FILE_IO_ERRORS, *JSON_PARSING_ERRORS) as e:
                # fallback-ok: skip unreadable or malformed mock response files
                if verbose:
                    click.echo(
                        f"Warning: Could not load mock response {response_file}: {e}",
                        err=True,
                    )

    return responses


def _find_mock_response_by_ticket_id(
    mock_responses: Mapping[str, dict[str, object]],
    ticket_id: str,  # string-id-ok: external ticket identifier from corpus data
    model_type: str = "candidate",
) -> dict[str, object] | None:
    """Find a mock response by ticket_id within a specific model type.

    Handles arbitrary JSON payloads safely by skipping non-dict values.

    Args:
        mock_responses: Dict of mock responses keyed as 'model_type/sample_stem'.
        ticket_id: The ticket ID to search for (e.g., 'TKT-2024-001').
        model_type: The model type to search in (e.g., 'candidate', 'baseline').

    Returns:
        The mock response dict if found, None otherwise.
    """
    for key, response in mock_responses.items():
        if not key.startswith(f"{model_type}/"):
            continue
        # NOTE(OMN-1397): Runtime safety check for JSON data that may not match declared types.
        if not isinstance(response, dict):
            # fallback-ok: skip malformed entries, search continues for valid matches
            continue  # type: ignore[unreachable]
        response_ticket_id = response.get("ticket_id")
        if response_ticket_id == ticket_id:
            return response
    return None


def _evaluate_confidence_invariant(
    sample: dict[str, object],
    mock_response: dict[str, object] | None,
    invariants: dict[str, object],
) -> tuple[bool, float | None, float]:
    """Evaluate confidence threshold invariant for a sample.

    Args:
        sample: Corpus sample dict with _category metadata.
        mock_response: Mock response dict with confidence field, or None.
        invariants: Invariants config dict with thresholds.

    Returns:
        Tuple of (passed, actual_confidence, required_threshold).
        If mock_response is None, returns (False, None, threshold).
    """
    # Get thresholds from invariants
    thresholds = invariants.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    confidence_min_raw = thresholds.get("confidence_min", 0.70)
    if isinstance(confidence_min_raw, (int, float)):
        confidence_min = float(confidence_min_raw)
    else:
        confidence_min = 0.70

    golden_confidence_min_raw = thresholds.get("golden_confidence_min", 0.85)
    if isinstance(golden_confidence_min_raw, (int, float)):
        golden_confidence_min = float(golden_confidence_min_raw)
    else:
        golden_confidence_min = 0.85

    # Determine required threshold based on sample category
    category = sample.get("_category", "")
    if category == "golden":
        required_threshold = golden_confidence_min
    else:
        # edge-cases and any other category use the default threshold
        required_threshold = confidence_min

    # If no mock response, fail
    if mock_response is None:
        return (False, None, required_threshold)

    # Extract confidence from mock response
    confidence_raw = mock_response.get("confidence")
    if confidence_raw is None:
        return (False, None, required_threshold)

    try:
        # NOTE(OMN-1397): dict.get() returns object type, but float() handles
        # int/float/str at runtime. TypeError/ValueError caught for invalid types.
        confidence = float(cast(int | float | str, confidence_raw))
    except (TypeError, ValueError):
        return (False, None, required_threshold)

    # Evaluate: confidence must meet or exceed threshold
    passed = confidence >= required_threshold
    return (passed, confidence, required_threshold)


@io_error_handling("Creating output bundle")
def _create_output_bundle(
    output_dir: Path,
    scenario_name: str,
    corpus: list[dict[str, object]],
    report: ModelDemoValidationReport,
) -> None:
    """Persist demo run artifacts to a structured output directory.

    Creates a reproducible output bundle containing all inputs, outputs, and reports
    for the demo run. Directory structure:
        output_dir/
            inputs/         - Numbered YAML corpus samples
            outputs/        - Numbered JSON evaluation results
            run_manifest.yaml - Run configuration metadata
            report.json     - Machine-readable validation report
            report.md       - Human-readable markdown report

    Args:
        output_dir: Target directory for the output bundle (created if needed).
        scenario_name: Name of the executed scenario for report headers.
        corpus: List of corpus samples to write to inputs/.
        report: Validation report model containing config, summary, and results.

    Raises:
        ModelOnexError: If directory creation or file writing fails.
    """
    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "inputs").mkdir(exist_ok=True)
    (output_dir / "outputs").mkdir(exist_ok=True)

    # Write run manifest
    manifest = {
        "scenario": scenario_name,
        "timestamp": report.config.timestamp,
        "seed": report.config.seed,
        "live_mode": report.config.live,
        "repeat": report.config.repeat,
        "corpus_count": len(corpus),
        "result_count": len(report.results),
    }
    with (output_dir / "run_manifest.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False)

    # Write corpus samples to inputs/
    for i, sample in enumerate(corpus):
        sample_file = output_dir / "inputs" / f"sample_{i + 1:03d}.yaml"
        with sample_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(sample, f, default_flow_style=False)

    # Write results to outputs/
    for i, result in enumerate(report.results):
        result_file = output_dir / "outputs" / f"sample_{i + 1:03d}.json"
        with result_file.open("w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)

    # Write report.json using canonical Pydantic model
    with (output_dir / "report.json").open("w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    # Write report.md
    _write_markdown_report(
        output_dir / "report.md", scenario_name, report.summary, report.results
    )


@io_error_handling("Writing markdown report")
def _write_markdown_report(
    path: Path,
    scenario_name: str,
    summary: ModelDemoSummary,
    results: list[ModelSampleResult],
) -> None:
    """Generate a human-readable markdown report for the demo run.

    Produces a formatted report with summary statistics, invariant pass/fail table,
    failure details, and sample results (limited to MAX_REPORT_SAMPLES to keep
    output manageable).

    Args:
        path: Output path for the markdown file.
        scenario_name: Scenario name for the report title.
        summary: ModelDemoSummary with totals, verdict, and invariant results.
        results: List of per-sample results to include in the report.

    Raises:
        ModelOnexError: If file writing fails.
    """
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# ONEX Demo Report: {scenario_name}\n\n")
        f.write(f"**Generated**: {datetime.now(UTC).isoformat()}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Samples**: {summary.total}\n")
        f.write(f"- **Passed**: {summary.passed}\n")
        f.write(f"- **Failed**: {summary.failed}\n")
        f.write(f"- **Pass Rate**: {summary.pass_rate:.1%}\n")
        f.write(f"- **Verdict**: {summary.verdict.value}\n")
        f.write(f"- **Recommendation**: {summary.recommendation}\n\n")

        if summary.invariant_results:
            f.write("## Invariant Results\n\n")
            f.write("| Invariant | Passed | Failed | Total | Rate |\n")
            f.write("|-----------|--------|--------|-------|------|\n")
            for inv_name, inv_result in summary.invariant_results.items():
                rate = (
                    inv_result.passed / inv_result.total if inv_result.total > 0 else 0
                )
                status = "✓" if inv_result.passed == inv_result.total else "⚠"
                f.write(
                    f"| {status} {inv_name} | {inv_result.passed} | {inv_result.failed} | {inv_result.total} | {rate:.0%} |\n"
                )
            f.write("\n")

        if summary.failures:
            f.write("## Failures\n\n")
            for failure in summary.failures:
                f.write(f"- **{failure.sample_id}** ({failure.invariant_id})")
                if failure.message:
                    f.write(f": {failure.message}")
                f.write("\n")
            f.write("\n")

        if results:
            f.write("## Sample Results\n\n")
            for i, result in enumerate(results[:MAX_REPORT_SAMPLES]):
                status = "✓" if result.passed else "✗"
                f.write(f"- {status} Sample {i + 1}: {result.sample_id}\n")
            if len(results) > MAX_REPORT_SAMPLES:
                f.write(f"\n... and {len(results) - MAX_REPORT_SAMPLES} more samples\n")


def _print_banner(scenario_name: str) -> None:
    """Print a visually distinct header banner for demo run output.

    Renders a 65-character wide banner with double-line borders and centered
    scenario name to clearly demarcate the start of demo execution output.

    Args:
        scenario_name: Name of the scenario to display in the banner.
    """
    width = 65
    click.echo("═" * width)
    title = f"ONEX DEMO: {scenario_name}"
    padding = (width - len(title)) // 2
    click.echo(" " * padding + title)
    click.echo("═" * width)
    click.echo()


def _print_results_summary(summary: ModelDemoSummary, output_dir: Path) -> None:
    """Print formatted results summary with colored verdict to terminal.

    Displays invariant-level statistics (pass/fail counts and rates), a color-coded
    verdict (green=PASS, yellow=REVIEW, red=FAIL), recommendation text, and paths
    to generated output files for user reference.

    Args:
        summary: ModelDemoSummary containing verdict, invariant results, and failures.
        output_dir: Path to output bundle for displaying file locations.
    """
    click.echo("─" * 65)
    click.echo("RESULTS")
    click.echo("─" * 65)

    if summary.invariant_results:
        for inv_name, inv_result in summary.invariant_results.items():
            rate = inv_result.passed / inv_result.total if inv_result.total > 0 else 0
            status = "✓" if inv_result.passed == inv_result.total else "⚠"
            rate_str = f"{rate:.0%}"
            failures = (
                "" if inv_result.failed == 0 else f" ← {inv_result.failed} failures"
            )
            click.echo(
                f"{status} {inv_name:<25} {inv_result.passed}/{inv_result.total} ({rate_str}){failures}"
            )

    click.echo()
    verdict = summary.verdict
    if verdict == EnumDemoVerdict.PASS:
        click.echo(click.style(f"Verdict: {verdict.value}", fg="green", bold=True))
    elif verdict == EnumDemoVerdict.REVIEW:
        click.echo(click.style(f"Verdict: {verdict.value}", fg="yellow", bold=True))
    else:
        click.echo(click.style(f"Verdict: {verdict.value}", fg="red", bold=True))

    click.echo(f"Recommendation: {summary.recommendation}")

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
    type=click.IntRange(min=1),
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
    demo_root = _get_demo_root()

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
    corpus = _load_corpus(corpus_dir, verbose=verbose)
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
        mock_responses = _load_mock_responses(mock_dir, verbose=verbose)

    # Load invariants
    invariants_path = scenario_path / "invariants.yaml"
    invariants: dict[str, object] = {}
    if invariants_path.is_file():
        try:
            with invariants_path.open(encoding="utf-8") as f:
                invariants = yaml.safe_load(f) or {}
        except (*FILE_IO_ERRORS, *YAML_PARSING_ERRORS) as e:
            # fallback-ok: use empty invariants if file is unreadable or malformed
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

    # Warn about skipped confidence checks in live mode (only once, before loop)
    thresholds_config = invariants.get("thresholds")
    if (
        live
        and verbose
        and isinstance(thresholds_config, dict)
        and thresholds_config.get("confidence_min") is not None
    ):
        click.echo(
            "Note: Confidence threshold checks skipped in live mode "
            "(requires mock responses)",
            err=True,
        )

    # Run evaluation (simplified for demo - actual implementation would use services)
    click.echo("Running evaluation...")

    results: list[ModelSampleResult] = []
    failures: list[ModelFailureDetail] = []
    passed_count = 0

    # Progress indicator
    total = len(corpus)
    last_progress = -1
    for i, sample in enumerate(corpus):
        # Simple progress bar - only update when visual bar changes
        progress = int((i + 1) / total * 40)
        if progress != last_progress:
            bar = "█" * progress + "░" * (40 - progress)
            click.echo(f"\rRunning replay... {bar} {i + 1}/{total}", nl=False)
            sys.stdout.flush()
            last_progress = progress

        # Simulate evaluation (in real implementation, use ServiceInvariantEvaluator)
        sample_id_raw = (
            sample.get("ticket_id") or sample.get("_source_file") or f"sample_{i + 1}"
        )
        sample_id = str(sample_id_raw)

        # Determine pass/fail and invariants checked
        passed = True
        invariants_checked: list[str] = []

        # Check confidence threshold invariant using mock responses
        # Skip in live mode - mock responses are only available in mock mode
        thresholds = invariants.get("thresholds")
        if (
            not live
            and isinstance(thresholds, dict)
            and thresholds.get("confidence_min") is not None
        ):
            # Find mock response by ticket_id
            mock_response = _find_mock_response_by_ticket_id(
                mock_responses, sample_id, model_type="candidate"
            )
            # Evaluate confidence against threshold
            conf_passed, actual_confidence, required_threshold = (
                _evaluate_confidence_invariant(sample, mock_response, invariants)
            )
            passed = conf_passed
            invariants_checked.append("confidence_threshold")

            # Track failure details if sample failed
            if not conf_passed:
                failures.append(
                    ModelFailureDetail(
                        sample_id=sample_id,
                        invariant_id="confidence_threshold",
                        expected=f"confidence >= {required_threshold:.2f}",
                        actual=f"confidence = {actual_confidence}"
                        if actual_confidence is not None
                        else "confidence = None (missing response)",
                        message="Confidence below threshold",
                    )
                )

        result = ModelSampleResult(
            sample_id=sample_id,
            passed=passed,
            invariants_checked=invariants_checked,
        )

        if passed:
            passed_count += 1

        results.append(result)

    click.echo()  # New line after progress bar
    click.echo()

    # Calculate summary
    total_samples = len(results)
    failed_count = total_samples - passed_count
    pass_rate = passed_count / total_samples if total_samples > 0 else 0

    # Determine verdict based on pass rate thresholds
    verdict: EnumDemoVerdict
    if pass_rate >= PASS_THRESHOLD:
        verdict = EnumDemoVerdict.PASS
    elif pass_rate >= REVIEW_THRESHOLD:
        verdict = EnumDemoVerdict.REVIEW
    else:
        verdict = EnumDemoVerdict.FAIL

    # Build invariant results with passed/failed/total
    invariant_results: dict[str, ModelInvariantResult] = {}
    if results:
        invariant_names: set[str] = set()
        for r in results:
            invariant_names.update(r.invariants_checked)
        for inv_name in invariant_names:
            inv_passed = sum(
                1 for r in results if r.passed and inv_name in r.invariants_checked
            )
            inv_total = sum(1 for r in results if inv_name in r.invariants_checked)
            inv_failed = inv_total - inv_passed
            invariant_results[inv_name] = ModelInvariantResult(
                passed=inv_passed,
                failed=inv_failed,
                total=inv_total,
            )

    # Build summary using Pydantic model
    summary = ModelDemoSummary(
        total=total_samples,
        passed=passed_count,
        failed=failed_count,
        pass_rate=pass_rate,
        verdict=verdict,
        invariant_results=invariant_results,
        failures=failures,
    )

    # Build config using Pydantic model
    config = ModelDemoConfig(
        scenario=scenario,
        live=live,
        seed=seed,
        repeat=repeat,
        timestamp=timestamp,
    )

    # Build the complete report using canonical Pydantic model
    report = ModelDemoValidationReport(
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        scenario=scenario,
        timestamp=timestamp,
        config=config,
        summary=summary,
        results=results,
    )

    # Create output bundle
    _create_output_bundle(output, scenario, corpus, report)

    # Print results
    _print_results_summary(summary, output)

    # Exit with appropriate code
    if verdict == EnumDemoVerdict.PASS:
        ctx.exit(EnumCLIExitCode.SUCCESS)
    else:
        ctx.exit(EnumCLIExitCode.ERROR)


__all__ = ["demo"]
