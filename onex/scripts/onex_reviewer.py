#!/usr/bin/env python3
"""
ONEX Opus Nightly Reviewer Agent
Deterministic, diff-driven code review using Opus 4.1
"""

import json
import os
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml


class ONEXReviewer:
    """Main ONEX reviewer implementation"""

    RULE_DEFINITIONS = {
        # Naming rules
        "ONEX.NAMING.PROTOCOL_001": {
            "severity": "error",
            "message": "Protocol class does not start with 'Protocol'",
            "pattern": r"^\+class\s+(?!Protocol)([A-Z][A-Za-z0-9_]*)\s*\(",
            "file_pattern": r"protocol_.*\.py$",
            "fix": "Rename to Protocol{}"
        },
        "ONEX.NAMING.MODEL_001": {
            "severity": "warning",
            "message": "Model class does not start with 'Model'",
            "pattern": r"^\+class\s+(?!Model)([A-Z][A-Za-z0-9_]*)\s*\(",
            "file_pattern": r"model_.*\.py$",
            "fix": "Rename to Model{}"
        },
        "ONEX.NAMING.ENUM_001": {
            "severity": "warning",
            "message": "Enum class does not start with 'Enum'",
            "pattern": r"^\+class\s+(?!Enum)([A-Z][A-Za-z0-9_]*)\s*\(",
            "file_pattern": r"enum_.*\.py$",
            "fix": "Rename to Enum{}"
        },
        "ONEX.NAMING.NODE_001": {
            "severity": "warning",
            "message": "Node class does not start with 'Node'",
            "pattern": r"^\+class\s+(?!Node)([A-Z][A-Za-z0-9_]*)\s*\(",
            "file_pattern": r"node_.*\.py$",
            "fix": "Rename to Node{}"
        },
        # Boundary rules
        "ONEX.BOUNDARY.FORBIDDEN_IMPORT_001": {
            "severity": "error",
            "message": "Forbidden import detected",
            "pattern": None,  # Dynamic based on policy
            "fix": "Remove forbidden import"
        },
        # SPI purity rules
        "ONEX.SPI.RUNTIMECHECKABLE_001": {
            "severity": "error",
            "message": "Protocol class missing @runtime_checkable decorator",
            "pattern": r"^\+class\s+Protocol([A-Z][A-Za-z0-9_]*)\s*\(",
            "file_pattern": r".*\.py$",
            "requires_context": True,
            "fix": "Add @runtime_checkable decorator"
        },
        "ONEX.SPI.FORBIDDEN_LIB_001": {
            "severity": "error",
            "message": "Forbidden library usage in SPI",
            "pattern": r"^\+.*(import\s+(os|pathlib|sqlite3|requests|httpx|socket)|from\s+(os|pathlib|sqlite3|requests|httpx|socket)|open\()",
            "file_pattern": r"src/omnibase[_-]spi/.*\.py$",
            "fix": "Remove forbidden library usage"
        },
        # Typing hygiene
        "ONEX.TYPE.UNANNOTATED_DEF_001": {
            "severity": "warning",
            "message": "Function definition lacks type annotations",
            "pattern": r"^\+def\s+[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)(?:\s*:|\s*->)?(?!\s*->)",
            "fix": "Add type annotations"
        },
        "ONEX.TYPE.ANY_001": {
            "severity": "warning",
            "message": "Usage of 'Any' type in non-test code",
            "pattern": r"^\+.*\bAny\b",
            "file_pattern": r"^(?!.*test).*\.py$",
            "fix": "Replace with specific type"
        },
        "ONEX.TYPE.OPTIONAL_ASSERT_001": {
            "severity": "warning",
            "message": "Optional type immediately asserted non-null",
            "pattern": r"^\+.*Optional\[.*\]",
            "requires_context": True,
            "fix": "Use non-optional type or handle None case"
        },
        # Waiver hygiene
        "ONEX.WAIVER.MALFORMED_001": {
            "severity": "warning",
            "message": "Malformed waiver comment",
            "pattern": r"^\+.*#\s*onex:ignore\s+\S+(?!.*reason=|.*expires=)",
            "fix": "Add reason= and expires= to waiver"
        },
        "ONEX.WAIVER.EXPIRED_001": {
            "severity": "error",
            "message": "Expired waiver",
            "pattern": r"^\+.*#\s*onex:ignore.*expires=(\d{4}-\d{2}-\d{2})",
            "requires_date_check": True,
            "fix": "Update or remove expired waiver"
        }
    }

    def __init__(self, mode: str, input_dir: str, policy_path: Optional[str] = None):
        self.mode = mode
        self.input_dir = Path(input_dir)
        self.policy_path = Path(policy_path) if policy_path else Path("onex/configs/policy.yaml")
        self.findings = []
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.repo_name = self._detect_repo_name()
        self.policy = self._load_policy()

    def _detect_repo_name(self) -> str:
        """Detect repository name from git or metadata"""
        metadata_path = self.input_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                return metadata.get("repo", "unknown")

        # Fallback to git detection
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, check=True
            )
            return Path(result.stdout.strip()).name
        except:
            return "unknown"

    def _load_policy(self) -> Dict:
        """Load policy configuration"""
        if not self.policy_path.exists():
            return {"ruleset_version": "0.1", "repos": {}, "settings": {}}

        with open(self.policy_path, 'r') as f:
            return yaml.safe_load(f)

    def _get_repo_forbids(self) -> List[str]:
        """Get forbidden import patterns for current repo"""
        # Try exact match first
        if self.repo_name in self.policy.get("repos", {}):
            return self.policy["repos"][self.repo_name].get("forbids", [])

        # Try with underscores replaced by hyphens
        alt_name = self.repo_name.replace("_", "-")
        if alt_name in self.policy.get("repos", {}):
            return self.policy["repos"][alt_name].get("forbids", [])

        # Try with hyphens replaced by underscores
        alt_name = self.repo_name.replace("-", "_")
        if alt_name in self.policy.get("repos", {}):
            return self.policy["repos"][alt_name].get("forbids", [])

        # Use default
        return self.policy.get("default", {}).get("forbids", [])

    def _generate_fingerprint(self, path: str, line: int, rule_id: str, evidence: str) -> str:
        """Generate stable fingerprint for finding"""
        content = f"{path}:{line}:{rule_id}:{evidence}"
        return hashlib.sha256(content.encode()).hexdigest()[:8]

    def _check_runtime_checkable(self, lines: List[str], class_line_idx: int) -> bool:
        """Check if @runtime_checkable exists within 5 lines before Protocol class"""
        start_idx = max(0, class_line_idx - 5)
        for i in range(start_idx, class_line_idx):
            if i < len(lines) and "@runtime_checkable" in lines[i]:
                return True
        return False

    def _check_optional_assert(self, lines: List[str], optional_line_idx: int) -> bool:
        """Check if Optional is immediately asserted non-null"""
        # Check next 3 lines for assert
        end_idx = min(len(lines), optional_line_idx + 4)
        for i in range(optional_line_idx + 1, end_idx):
            if "assert" in lines[i] and "is not None" in lines[i]:
                return True
        return False

    def _check_waiver_expiry(self, waiver_date: str) -> bool:
        """Check if waiver has expired"""
        try:
            expires = datetime.strptime(waiver_date, "%Y-%m-%d")
            today = datetime.strptime(self.today, "%Y-%m-%d")
            return expires < today
        except:
            return False

    def _analyze_diff_chunk(self, diff_content: str, current_file: str = "") -> List[Dict]:
        """Analyze a diff chunk for violations"""
        chunk_findings = []
        lines = diff_content.split('\n')
        current_line_num = 0

        for idx, line in enumerate(lines):
            # Track file changes
            if line.startswith("diff --git"):
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[3].lstrip("b/")
                    current_line_num = 0
                continue

            # Track line numbers
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line_num = int(match.group(1))
                continue

            # Only process added lines
            if not line.startswith("+"):
                if line.startswith("-"):
                    continue
                current_line_num += 1
                continue

            current_line_num += 1

            # Check each rule
            for rule_id, rule_def in self.RULE_DEFINITIONS.items():
                # Skip if file pattern doesn't match
                if "file_pattern" in rule_def:
                    if not re.search(rule_def["file_pattern"], current_file):
                        continue

                # Special handling for boundary checks
                if rule_id == "ONEX.BOUNDARY.FORBIDDEN_IMPORT_001":
                    forbids = self._get_repo_forbids()
                    for forbid_pattern in forbids:
                        if re.search(forbid_pattern, line):
                            finding = {
                                "ruleset_version": "0.1",
                                "rule_id": rule_id,
                                "severity": rule_def["severity"],
                                "repo": self.repo_name,
                                "path": current_file,
                                "line": current_line_num,
                                "message": rule_def["message"],
                                "evidence": {"import_line": line.strip()},
                                "suggested_fix": rule_def["fix"],
                                "fingerprint": self._generate_fingerprint(
                                    current_file, current_line_num, rule_id, line.strip()
                                )
                            }
                            chunk_findings.append(finding)
                    continue

                # Skip if no pattern
                if not rule_def.get("pattern"):
                    continue

                # Check pattern match
                match = re.search(rule_def["pattern"], line)
                if not match:
                    continue

                # Handle context requirements
                if rule_def.get("requires_context"):
                    if rule_id == "ONEX.SPI.RUNTIMECHECKABLE_001":
                        if not self._check_runtime_checkable(lines, idx):
                            finding = {
                                "ruleset_version": "0.1",
                                "rule_id": rule_id,
                                "severity": rule_def["severity"],
                                "repo": self.repo_name,
                                "path": current_file,
                                "line": current_line_num,
                                "message": rule_def["message"],
                                "evidence": {"class_name": match.group(1) if match.groups() else "Protocol"},
                                "suggested_fix": rule_def["fix"],
                                "fingerprint": self._generate_fingerprint(
                                    current_file, current_line_num, rule_id, line.strip()
                                )
                            }
                            chunk_findings.append(finding)
                    elif rule_id == "ONEX.TYPE.OPTIONAL_ASSERT_001":
                        if self._check_optional_assert(lines, idx):
                            finding = {
                                "ruleset_version": "0.1",
                                "rule_id": rule_id,
                                "severity": rule_def["severity"],
                                "repo": self.repo_name,
                                "path": current_file,
                                "line": current_line_num,
                                "message": rule_def["message"],
                                "evidence": {"line": line.strip()},
                                "suggested_fix": rule_def["fix"],
                                "fingerprint": self._generate_fingerprint(
                                    current_file, current_line_num, rule_id, line.strip()
                                )
                            }
                            chunk_findings.append(finding)
                    continue

                # Handle date checks
                if rule_def.get("requires_date_check"):
                    if rule_id == "ONEX.WAIVER.EXPIRED_001":
                        date_match = re.search(r"expires=(\d{4}-\d{2}-\d{2})", line)
                        if date_match and self._check_waiver_expiry(date_match.group(1)):
                            finding = {
                                "ruleset_version": "0.1",
                                "rule_id": rule_id,
                                "severity": rule_def["severity"],
                                "repo": self.repo_name,
                                "path": current_file,
                                "line": current_line_num,
                                "message": rule_def["message"],
                                "evidence": {"expiry_date": date_match.group(1)},
                                "suggested_fix": rule_def["fix"],
                                "fingerprint": self._generate_fingerprint(
                                    current_file, current_line_num, rule_id, line.strip()
                                )
                            }
                            chunk_findings.append(finding)
                    continue

                # Create finding for regular rules
                evidence = {}
                if match.groups():
                    evidence["match"] = match.group(1)
                else:
                    evidence["line"] = line.strip()

                finding = {
                    "ruleset_version": "0.1",
                    "rule_id": rule_id,
                    "severity": rule_def["severity"],
                    "repo": self.repo_name,
                    "path": current_file,
                    "line": current_line_num,
                    "message": rule_def["message"],
                    "evidence": evidence,
                    "suggested_fix": rule_def["fix"].format(match.group(1)) if match.groups() and "{}" in rule_def["fix"] else rule_def["fix"],
                    "fingerprint": self._generate_fingerprint(
                        current_file, current_line_num, rule_id, line.strip()
                    )
                }
                chunk_findings.append(finding)

        return chunk_findings

    def _generate_summary(self, findings: List[Dict], truncated: bool = False) -> str:
        """Generate markdown summary"""
        # Count findings by severity and type
        error_count = sum(1 for f in findings if f["severity"] == "error")
        warning_count = sum(1 for f in findings if f["severity"] == "warning")

        # Count by category
        naming_count = sum(1 for f in findings if "NAMING" in f["rule_id"])
        boundary_count = sum(1 for f in findings if "BOUNDARY" in f["rule_id"])
        spi_count = sum(1 for f in findings if "SPI" in f["rule_id"])
        type_count = sum(1 for f in findings if "TYPE" in f["rule_id"])
        waiver_count = sum(1 for f in findings if "WAIVER" in f["rule_id"])

        # Calculate risk score (0-100)
        risk_score = min(100, error_count * 15 + warning_count * 5)

        # Build summary
        summary = []
        summary.append("## Executive summary")
        summary.append(f"Risk score: {risk_score}")
        summary.append(f"- {error_count} errors, {warning_count} warnings")
        summary.append(f"- {boundary_count} boundary, {naming_count} naming, {spi_count} SPI, {type_count} typing, {waiver_count} waiver")

        # Top violations
        summary.append("\n## Top violations")
        if findings:
            # Show up to 5 most critical findings
            top_findings = sorted(findings, key=lambda x: (x["severity"] == "warning", x["rule_id"]))[:5]
            for finding in top_findings:
                summary.append(f"- {finding['message']} in {finding['path']}:{finding['line']}")
        else:
            summary.append("- No violations detected")

        # Waiver issues
        summary.append("\n## Waiver issues")
        waiver_findings = [f for f in findings if "WAIVER" in f["rule_id"]]
        if waiver_findings:
            for finding in waiver_findings[:3]:
                summary.append(f"- {finding['message']} in {finding['path']}:{finding['line']}")
        else:
            summary.append("- No waiver issues")

        # Next actions
        summary.append("\n## Next actions")
        if error_count > 0:
            summary.append(f"- Fix {error_count} errors blocking compliance")
        if warning_count > 0:
            summary.append(f"- Review {warning_count} warnings for quality improvement")
        if not findings:
            summary.append("- No actions required")

        # Coverage notes
        summary.append("\n## Coverage")
        if truncated:
            summary.append("- Note: Diff was truncated due to size limits")
        if self.mode == "baseline":
            summary.append(f"- Baseline analysis of {self.repo_name} repository")
        else:
            summary.append(f"- Incremental review of changes in {self.repo_name}")

        return "\n".join(summary)

    def run(self) -> Tuple[str, str]:
        """Run the review process"""
        if self.mode == "baseline":
            return self._run_baseline()
        else:
            return self._run_nightly()

    def _run_baseline(self) -> Tuple[str, str]:
        """Run baseline analysis"""
        # Process sharded diffs
        shards_dir = self.input_dir / "shards"
        if shards_dir.exists():
            for shard_file in sorted(shards_dir.glob("diff_shard_*.diff")):
                with open(shard_file, 'r', errors='ignore') as f:
                    diff_content = f.read()
                    shard_findings = self._analyze_diff_chunk(diff_content)
                    self.findings.extend(shard_findings)
        else:
            # Single diff file
            diff_file = self.input_dir / "baseline.diff"
            if diff_file.exists():
                with open(diff_file, 'r', errors='ignore') as f:
                    diff_content = f.read()
                    self.findings = self._analyze_diff_chunk(diff_content)

        # Generate outputs
        ndjson_output = "\n".join(json.dumps(f, ensure_ascii=True) for f in self.findings)
        summary = self._generate_summary(self.findings)

        return ndjson_output, summary

    def _run_nightly(self) -> Tuple[str, str]:
        """Run nightly incremental analysis"""
        diff_file = self.input_dir / "nightly.diff"
        if not diff_file.exists():
            return "", "## No changes to review"

        with open(diff_file, 'r', errors='ignore') as f:
            diff_content = f.read()

        # Check if truncated
        truncated = False
        metadata_file = self.input_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                truncated = metadata.get("truncated", False)

        self.findings = self._analyze_diff_chunk(diff_content)

        # Generate outputs
        ndjson_output = "\n".join(json.dumps(f, ensure_ascii=True) for f in self.findings)
        summary = self._generate_summary(self.findings, truncated)

        return ndjson_output, summary

    def update_marker(self):
        """Update the nightly marker after successful run"""
        if self.mode != "nightly":
            return

        next_sha_file = self.input_dir / "next_sha"
        if not next_sha_file.exists():
            return

        state_dir = Path(".onex_nightly")
        state_dir.mkdir(exist_ok=True)

        with open(next_sha_file, 'r') as f:
            next_sha = f.read().strip()

        marker_file = state_dir / "last_successful_sha"
        with open(marker_file, 'w') as f:
            f.write(next_sha)

        print(f"Updated marker to SHA: {next_sha}")


def main():
    if len(sys.argv) < 3:
        print("Usage: onex_reviewer.py <mode> <input_dir> [policy_file]")
        print("  mode: 'baseline' or 'nightly'")
        print("  input_dir: Directory containing producer outputs")
        print("  policy_file: Optional path to policy.yaml")
        sys.exit(1)

    mode = sys.argv[1]
    input_dir = sys.argv[2]
    policy_file = sys.argv[3] if len(sys.argv) > 3 else None

    if mode not in ["baseline", "nightly"]:
        print(f"Error: Invalid mode '{mode}'. Use 'baseline' or 'nightly'")
        sys.exit(1)

    if not Path(input_dir).exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)

    # Run reviewer
    reviewer = ONEXReviewer(mode, input_dir, policy_file)
    ndjson_output, summary = reviewer.run()

    # Output results
    print(ndjson_output)
    print("---ONEX-SEP---")
    print(summary)

    # Save to files
    output_dir = Path(input_dir) / "outputs"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "findings.ndjson", 'w') as f:
        f.write(ndjson_output)

    with open(output_dir / "summary.md", 'w') as f:
        f.write(summary)

    # Update marker for successful nightly runs
    if mode == "nightly":
        reviewer.update_marker()

    print(f"\nResults saved to: {output_dir}")
    sys.exit(0 if not reviewer.findings else 1)


if __name__ == "__main__":
    main()