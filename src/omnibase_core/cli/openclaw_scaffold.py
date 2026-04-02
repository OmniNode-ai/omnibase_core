# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OpenClaw scaffold generator — generates ONEX contract packages from analysis reports."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.cli.openclaw_analyzer import OpenClawAnalysis

# npm dependency -> Python equivalent mapping
NPM_TO_PYTHON: dict[str, str] = {
    "axios": "httpx",
    "node-fetch": "httpx",
    "fs-extra": "",  # stdlib pathlib
    "execa": "",  # stdlib subprocess
    "shelljs": "",  # stdlib subprocess
    "lodash": "",  # stdlib or no equivalent needed
    "chalk": "rich",
    "inquirer": "click",
    "aws-sdk": "boto3",
    "@aws-sdk/client-s3": "boto3",
    "stripe": "stripe",
    "@google-cloud/storage": "google-cloud-storage",
}

# JS API -> Python equivalent mapping
JS_TO_PYTHON_API: dict[str, str] = {
    "fs.readFile": "pathlib.Path.read_text",
    "fs.writeFile": "pathlib.Path.write_text",
    "fs.readdir": "pathlib.Path.iterdir",
    "fs.mkdir": "pathlib.Path.mkdir",
    "fs.unlink": "pathlib.Path.unlink",
    "child_process.exec": "subprocess.run",
    "child_process.spawn": "subprocess.Popen",
    "fetch": "httpx.AsyncClient.request",
    "axios.get": "httpx.AsyncClient.get",
    "axios.post": "httpx.AsyncClient.post",
}


def _resolve_python_deps(npm_deps: dict[str, str]) -> list[str]:
    """Map npm dependencies to Python equivalents."""
    python_deps: list[str] = []
    for npm_name in npm_deps:
        py_equiv = NPM_TO_PYTHON.get(npm_name, "")
        if py_equiv:
            python_deps.append(py_equiv)
    return sorted(set(python_deps))


def _build_api_mappings(
    capabilities: list[object],
) -> list[dict[str, str]]:
    """Build JS->Python API mapping list from capabilities."""
    mappings: list[dict[str, str]] = []
    seen: set[str] = set()
    for cap in capabilities:
        details = getattr(cap, "details", "")
        # Strip trailing () for lookup
        lookup_key = details.rstrip("()")
        if lookup_key in JS_TO_PYTHON_API and lookup_key not in seen:
            seen.add(lookup_key)
            mappings.append({"js": lookup_key, "python": JS_TO_PYTHON_API[lookup_key]})
    return mappings


def _get_template_dir() -> Path:
    """Return the path to the ported_skill template directory."""
    return Path(__file__).parent / "templates" / "ported_skill"


def generate_contract_package(
    analysis: OpenClawAnalysis,
    output_dir: Path,
) -> Path:
    """Generate a pip-installable ONEX contract package from analysis.

    Args:
        analysis: The analyzed OpenClaw package metadata and capabilities.
        output_dir: Where to write the generated package.

    Returns:
        Path to the generated package directory.
    """
    from jinja2 import Environment, FileSystemLoader

    template_dir = _get_template_dir()
    env = Environment(  # noqa: S701  # code-gen templates, not HTML
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )

    # Normalize package name
    pkg_name = (
        analysis.name.replace("@", "")
        .replace("/", "-")
        .replace("openclaw-", "omniclaw-")
    )
    if not pkg_name.startswith("omniclaw-"):
        pkg_name = f"omniclaw-{pkg_name}"

    node_name = f"node_ported_{pkg_name.replace('-', '_')}"

    context = {
        "pkg_name": pkg_name,
        "node_name": node_name,
        "description": analysis.description,
        "version": analysis.version,
        "capabilities": analysis.capabilities,
        "env_vars": analysis.env_vars,
        "security_tier": analysis.security_tier,
        "confidence_level": analysis.confidence_level,
        "python_deps": _resolve_python_deps(analysis.npm_dependencies),
        "api_mappings": _build_api_mappings(analysis.capabilities),
    }

    # Create directory structure
    pkg_dir = output_dir / pkg_name
    src_dir = pkg_dir / "src" / node_name
    handlers_dir = src_dir / "handlers"
    tests_dir = pkg_dir / "tests"

    src_dir.mkdir(parents=True, exist_ok=True)
    handlers_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)

    # Template -> output path mapping
    file_map = {
        "contract.yaml.j2": src_dir / "contract.yaml",
        "node.py.j2": src_dir / "node.py",
        "handler.py.j2": handlers_dir / "handler_ported.py",
        "test_golden_chain.py.j2": tests_dir / "test_golden_chain.py",
        "pyproject.toml.j2": pkg_dir / "pyproject.toml",
    }

    # Create __init__.py files
    (src_dir / "__init__.py").write_text(
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
    )
    (handlers_dir / "__init__.py").write_text(
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
    )

    for template_name, output_path in file_map.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)
        output_path.write_text(rendered)

    return pkg_dir
