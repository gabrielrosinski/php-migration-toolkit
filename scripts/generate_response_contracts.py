#!/usr/bin/env python3
"""Generate response contracts from legacy_analysis.json with return structures.

This script generates response contracts documenting input/output for each route
with field types, addressing the gap where ARCHITECTURE.md doesn't specify
response contracts.

Usage:
    python scripts/generate_response_contracts.py \
        -a output/analysis/legacy_analysis.json \
        -r output/analysis/routes.json \
        -o output/analysis/response_contracts.json
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List


def generate_contracts(analysis_path: str, routes_path: str, output_path: str):
    """Generate response contracts JSON from analysis and routes."""

    with open(analysis_path) as f:
        analysis = json.load(f)
    with open(routes_path) as f:
        routes = json.load(f)

    contracts = {}

    # Build function lookup with return structures
    func_lookup = {}
    for file_data in analysis.get('all_files', []):
        for func in file_data.get('functions', []):
            func_lookup[func['name']] = {
                'return_type': func.get('return_type'),
                'return_array_keys': func.get('return_array_keys', []),
                'return_nested_keys': func.get('return_nested_keys', {}),
                'params': func.get('params', []),
                'source_file': file_data.get('path', file_data.get('relative_path', 'unknown'))
            }

    # Map routes to response contracts
    for route in routes.get('routes', []):
        route_key = f"{route.get('method', 'GET')} {route.get('path', '/')}"
        handler = route.get('handler', '')

        # Find handler function
        func_info = func_lookup.get(handler, {})

        contracts[route_key] = {
            'method': route.get('method', 'GET'),
            'path': route.get('path', '/'),
            'handler': handler,
            'source_file': func_info.get('source_file', route.get('source_file', 'unknown')),
            'request': {
                'params': route.get('params', []),
                'query': route.get('query_params', []),
                'body': route.get('body_fields', [])
            },
            'response': {
                'type': func_info.get('return_type', 'unknown'),
                'fields': func_info.get('return_array_keys', []),
                'nested': func_info.get('return_nested_keys', {})
            }
        }

    # Write contracts
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(contracts, f, indent=2)

    print(f"Generated response contracts: {output_file}")
    print(f"  Total routes: {len(contracts)}")

    # Count routes with return info
    routes_with_fields = sum(1 for c in contracts.values() if c['response']['fields'])
    print(f"  Routes with return fields: {routes_with_fields}")

    # Also append to ARCHITECTURE.md if it exists
    arch_path = output_file.parent / 'ARCHITECTURE.md'
    if arch_path.exists():
        append_contracts_to_architecture(contracts, arch_path)


def append_contracts_to_architecture(contracts: Dict, arch_path: Path):
    """Append response contracts section to ARCHITECTURE.md"""

    # Check if section already exists
    content = arch_path.read_text()
    if '## Response Contracts (Auto-Generated)' in content:
        print(f"  ARCHITECTURE.md already has Response Contracts section, skipping append")
        return

    section = "\n\n## Response Contracts (Auto-Generated)\n\n"
    section += "| Route | Response Type | Fields |\n"
    section += "|-------|---------------|--------|\n"

    for route_key, contract in sorted(contracts.items()):
        fields = ', '.join(contract['response']['fields'][:5])
        if len(contract['response']['fields']) > 5:
            fields += f" (+{len(contract['response']['fields']) - 5} more)"
        if not fields:
            fields = "_unknown_"
        section += f"| `{route_key}` | {contract['response']['type'] or 'unknown'} | {fields} |\n"

    with open(arch_path, 'a') as f:
        f.write(section)

    print(f"  Appended Response Contracts section to: {arch_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate response contracts from legacy analysis and routes'
    )
    parser.add_argument('-a', '--analysis', required=True,
                        help='Path to legacy_analysis.json')
    parser.add_argument('-r', '--routes', required=True,
                        help='Path to routes.json')
    parser.add_argument('-o', '--output', required=True,
                        help='Output path for response_contracts.json')
    args = parser.parse_args()
    generate_contracts(args.analysis, args.routes, args.output)
