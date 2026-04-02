# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OpenClaw capability analyzer — reads npm skill packages and detects capabilities."""

from __future__ import annotations

import json
import re
from pathlib import Path

from omnibase_core.cli.openclaw_analysis import OpenClawAnalysis
from omnibase_core.cli.openclaw_capability import OpenClawCapability

__all__ = ["OpenClawAnalysis", "OpenClawCapability", "analyze_openclaw_package"]


# Detection patterns: (regex, details_template, security_tier)
# details_template can use group references
CAPABILITY_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "file_access": [
        (
            r"fs\.(readFile|writeFile|readdir|mkdir|unlink|stat|access)",
            "fs.{0}",
            "sandboxed",
        ),
        (r"fs\.promises\.(\w+)", "fs.promises.{0}", "sandboxed"),
        (r"path\.(join|resolve|dirname|basename)", "path.{0}", "safe"),
    ],
    "api_calls": [
        (r"fetch\s*\(", "fetch()", "privileged"),
        (r"axios\.(\w+)\s*\(", "axios.{0}()", "privileged"),
        (r"http\.request\s*\(", "http.request()", "privileged"),
    ],
    "shell_commands": [
        (
            r"child_process\.(exec|spawn|execSync|spawnSync)",
            "child_process.{0}",
            "privileged",
        ),
        (r"execa\s*\(", "execa()", "privileged"),
        (r"shelljs\.(\w+)", "shelljs.{0}", "privileged"),
    ],
    "env_vars": [
        (r"process\.env\.(\w+)", "process.env.{0}", "safe"),
    ],
    "database": [
        (r"(SELECT|INSERT|UPDATE|DELETE)\s+", "SQL: {0}", "privileged"),
        (r"mongoose\.\w+", "mongoose ORM", "privileged"),
        (r"sequelize\.\w+", "sequelize ORM", "privileged"),
    ],
    "sdk": [
        (r"aws-sdk|@aws-sdk/", "AWS SDK", "privileged"),
        (r"@google-cloud/", "Google Cloud SDK", "privileged"),
        (r"stripe\.", "Stripe SDK", "privileged"),
    ],
}

# Tier ordering for determining overall security tier
TIER_ORDER = {"safe": 0, "sandboxed": 1, "privileged": 2, "blocked": 3}


def _scan_source_file(
    file_path: Path,
    relative_path: str,
) -> tuple[list[OpenClawCapability], list[str]]:
    """Scan a single JS/TS source file for capability patterns.

    Returns:
        Tuple of (capabilities, env_vars).
    """
    capabilities: list[OpenClawCapability] = []
    env_vars: list[str] = []

    try:
        content = file_path.read_text(errors="replace")
    except OSError:
        return capabilities, env_vars

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        for category, patterns in CAPABILITY_PATTERNS.items():
            for pattern, details_template, tier in patterns:
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    details = (
                        details_template.format(*groups) if groups else details_template
                    )
                    capabilities.append(
                        OpenClawCapability(
                            category=category,
                            details=details,
                            security_tier=tier,
                            source_line=line_num,
                            source_file=relative_path,
                        )
                    )

                    # Extract env var names specifically
                    if category == "env_vars" and groups:
                        env_vars.append(groups[0])

    return capabilities, env_vars


def _determine_confidence(
    capabilities: list[OpenClawCapability],
    has_obfuscated: bool,
) -> str:
    """Determine the migration confidence level based on detected capabilities."""
    if has_obfuscated:
        return "blocked"

    if not capabilities:
        return "safely_auto_convertible"

    tiers = {cap.security_tier for cap in capabilities}

    if "blocked" in tiers:
        return "blocked"

    # Many privileged capabilities → manual review
    privileged_count = sum(1 for c in capabilities if c.security_tier == "privileged")
    categories = {c.category for c in capabilities}

    if privileged_count > 5 or len(categories) > 3:
        return "requires_manual_review"

    if tiers <= {"safe", "sandboxed"}:
        return "scaffoldable"

    if privileged_count <= 2:
        return "scaffoldable"

    return "requires_manual_review"


def analyze_openclaw_package(package_dir: Path) -> OpenClawAnalysis:
    """Read an OpenClaw npm package and extract its capabilities.

    Args:
        package_dir: Path to the npm package root (containing package.json).

    Returns:
        Structured analysis of the package's capabilities and metadata.

    Raises:
        FileNotFoundError: If package.json is missing.
        ValueError: If package.json is malformed.
    """
    package_json_path = package_dir / "package.json"
    if not package_json_path.exists():
        msg = f"No package.json found in {package_dir}"
        raise FileNotFoundError(msg)  # error-ok: CLI boundary input validation

    package_json = json.loads(package_json_path.read_text())
    if not isinstance(package_json, dict):
        msg = f"package.json in {package_dir} is not a JSON object"
        raise ValueError(msg)  # error-ok: CLI boundary input validation

    name = package_json.get("name", "unknown")
    version = package_json.get("version", "0.0.0")
    description = package_json.get("description", "")
    entry_point = package_json.get("main", "index.js")
    npm_deps = package_json.get("dependencies", {})

    # Read manifest.json if present (declared capabilities)
    manifest_path = package_dir / "manifest.json"
    manifest_capabilities: list[str] = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            if isinstance(manifest, dict):
                manifest_capabilities = manifest.get("capabilities", [])
        except (json.JSONDecodeError, OSError):
            pass

    # Scan JS/TS source files
    all_capabilities: list[OpenClawCapability] = []
    all_env_vars: list[str] = []
    has_obfuscated = False

    source_extensions = {".js", ".ts", ".mjs", ".cjs"}
    for source_file in package_dir.rglob("*"):
        if source_file.suffix not in source_extensions:
            continue
        # Skip node_modules
        if "node_modules" in source_file.parts:
            continue

        relative = str(source_file.relative_to(package_dir))

        # Check for obfuscation markers
        try:
            content = source_file.read_text(errors="replace")
            if _is_likely_obfuscated(content):
                has_obfuscated = True
        except OSError:
            continue

        caps, envs = _scan_source_file(source_file, relative)
        all_capabilities.extend(caps)
        all_env_vars.extend(envs)

    # Deduplicate env vars
    unique_env_vars = sorted(set(all_env_vars))

    # Determine overall security tier
    overall_tier = "safe"
    for cap in all_capabilities:
        if TIER_ORDER.get(cap.security_tier, 0) > TIER_ORDER.get(overall_tier, 0):
            overall_tier = cap.security_tier

    # Determine confidence level
    confidence = _determine_confidence(all_capabilities, has_obfuscated)

    return OpenClawAnalysis(
        name=name,
        version=version,
        description=description,
        entry_point=entry_point,
        capabilities=all_capabilities,
        env_vars=unique_env_vars,
        npm_dependencies=npm_deps,
        security_tier=overall_tier,
        confidence_level=confidence,
    )


def _is_likely_obfuscated(content: str) -> bool:
    """Heuristic check for obfuscated JavaScript source."""
    if len(content) == 0:
        return False

    lines = content.splitlines()
    if not lines:
        return False

    # Single very long line (>5000 chars) is suspicious
    max_line_len = max(len(line) for line in lines)
    if max_line_len > 5000 and len(lines) < 10:
        return True

    # High ratio of hex escapes
    hex_count = len(re.findall(r"\\x[0-9a-fA-F]{2}", content))
    if hex_count > 50:
        return True

    return False
