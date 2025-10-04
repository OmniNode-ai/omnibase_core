#!/usr/bin/env python3
"""
Analyze omnibase_spi protocol usage in omnibase_core.
"""
import ast
import re
from pathlib import Path
from collections import defaultdict
import json

BASE_DIR = Path("/root/repo/src/omnibase_core")

# Known omnibase_spi protocols based on imports found
KNOWN_PROTOCOLS = {
    'ProtocolLogger': 'logging protocol',
    'ProtocolWorkflowReducer': 'core workflow reducer',
    'protocol_core_types': 'core type protocols',
    'core_types': 'type system protocols',
}

class ProtocolAnalyzer(ast.NodeVisitor):
    """Analyze protocol usage in files"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.spi_imports = []
        self.protocol_usage = []
        self.type_checking_imports = []

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if 'omnibase_spi' in module:
            for alias in node.names:
                import_info = {
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'file': self.file_path
                }
                self.spi_imports.append(import_info)
        self.generic_visit(node)

    def visit_If(self, node):
        """Check for TYPE_CHECKING blocks"""
        if isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
            # This is a TYPE_CHECKING block
            for item in node.body:
                if isinstance(item, ast.ImportFrom):
                    module = item.module or ""
                    if 'omnibase_spi' in module:
                        for alias in item.names:
                            self.type_checking_imports.append({
                                'module': module,
                                'name': alias.name,
                                'in_type_checking': True,
                                'file': self.file_path
                            })
        self.generic_visit(node)

def analyze_protocol_usage():
    """Analyze all protocol usage"""
    all_spi_imports = []
    all_type_checking_imports = []
    files_using_protocols = []

    for py_file in BASE_DIR.rglob("*.py"):
        if 'archive' in py_file.parts:
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            analyzer = ProtocolAnalyzer(str(py_file))
            analyzer.visit(tree)

            if analyzer.spi_imports or analyzer.type_checking_imports:
                files_using_protocols.append(str(py_file))
                all_spi_imports.extend(analyzer.spi_imports)
                all_type_checking_imports.extend(analyzer.type_checking_imports)

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    # Group imports by protocol
    imports_by_protocol = defaultdict(list)
    for imp in all_spi_imports:
        imports_by_protocol[imp['name']].append(imp['file'])

    for imp in all_type_checking_imports:
        imports_by_protocol[imp['name']].append(imp['file'])

    return {
        'total_files_using_protocols': len(files_using_protocols),
        'files_using_protocols': files_using_protocols,
        'imports_by_protocol': {k: list(set(v)) for k, v in imports_by_protocol.items()},
        'all_imports': all_spi_imports,
        'type_checking_imports': all_type_checking_imports,
    }

def check_protocol_implementations():
    """Check which models should implement protocols"""
    # Models that look like they should implement protocols
    candidates = []

    for py_file in BASE_DIR.rglob("*.py"):
        if 'archive' in py_file.parts:
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for logger-like classes
            if re.search(r'class.*Logger.*BaseModel', content):
                candidates.append({
                    'file': str(py_file),
                    'type': 'logger',
                    'suggested_protocol': 'ProtocolLogger',
                    'reason': 'Logger class found'
                })

            # Check for reducer-like classes
            if re.search(r'class.*Reducer.*BaseModel', content):
                candidates.append({
                    'file': str(py_file),
                    'type': 'reducer',
                    'suggested_protocol': 'ProtocolWorkflowReducer',
                    'reason': 'Reducer class found'
                })

            # Check for workflow-related classes
            if re.search(r'class.*Workflow.*BaseModel', content):
                candidates.append({
                    'file': str(py_file),
                    'type': 'workflow',
                    'suggested_protocol': 'ProtocolWorkflowReducer or related',
                    'reason': 'Workflow class found'
                })

        except Exception:
            pass

    return candidates

def main():
    print("=== Analyzing Protocol Usage ===")

    usage = analyze_protocol_usage()
    candidates = check_protocol_implementations()

    results = {
        'protocol_usage': usage,
        'protocol_implementation_candidates': candidates,
        'summary': {
            'files_importing_protocols': usage['total_files_using_protocols'],
            'unique_protocols_imported': len(usage['imports_by_protocol']),
            'protocol_implementation_candidates': len(candidates),
        }
    }

    output_file = "/root/repo/protocol_audit_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Files importing protocols: {results['summary']['files_importing_protocols']}")
    print(f"  Unique protocols imported: {results['summary']['unique_protocols_imported']}")
    print(f"  Protocol implementation candidates: {results['summary']['protocol_implementation_candidates']}")

    print(f"\nProtocols imported:")
    for protocol, files in usage['imports_by_protocol'].items():
        print(f"  - {protocol}: used in {len(files)} file(s)")

if __name__ == "__main__":
    main()
